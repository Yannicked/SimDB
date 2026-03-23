"""convert_array_metadata_to_range_dicts

Convert numeric JSON arrays stored in the metadata column to
{"min": …, "mean": …, "max": …} range dicts so that they can be
queried efficiently using the JSON column operators.

Arrays may contain the special strings "nan", "inf" / "infinity" and
"-inf" / "-infinity" (written by the previous migration when numpy
arrays contained non-finite values).  These strings are treated as
non-finite and excluded from the range calculation, matching the
behaviour of ``Simulation._array_to_range()`` which uses
``numpy.isfinite()``.

Revision ID: a1b2c3d4e5f6
Revises: 28bee3aa2429
Create Date: 2026-03-23 00:00:00.000000

"""

import json
import math
from typing import Any, Dict, List, Optional, Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "28bee3aa2429"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Strings that the previous migration wrote for non-finite numpy values.
# Keys are lower-cased for case-insensitive matching.
_SPECIAL_FLOAT_STRINGS = {
    "nan": math.nan,
    "inf": math.inf,
    "infinity": math.inf,
    "-inf": -math.inf,
    "-infinity": -math.inf,
}


def _coerce_finite(value: Any) -> Optional[float]:
    """
    Return *value* as a finite float, or ``None`` if it is non-finite or
    cannot be interpreted as a number.

    Handles:
    - Plain int / float values (non-finite floats → None)
    - The special strings "nan", "inf", "infinity", "-inf", "-infinity"
      (case-insensitive) → None  (they are non-finite by definition)
    - bool is excluded (it is a subclass of int but not a numeric metadata value)
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) else None
    if isinstance(value, str):
        special = _SPECIAL_FLOAT_STRINGS.get(value.strip().lower())
        if special is not None:
            # All special strings map to non-finite floats → exclude
            return None
        # Try parsing as a plain numeric string
        try:
            f = float(value)
            return f if math.isfinite(f) else None
        except ValueError:
            return None
    return None


def _is_numeric_list(lst: list) -> bool:
    """
    Return True if *every* element of *lst* is either a finite number or one
    of the recognised non-finite string representations.  Pure string lists
    (e.g. lists of IDS names) must not be converted.
    """
    for v in lst:
        if isinstance(v, bool):
            return False
        if isinstance(v, (int, float)):
            continue
        if isinstance(v, str) and v.strip().lower() in _SPECIAL_FLOAT_STRINGS:
            continue
        # Try parsing as a number
        try:
            float(v)
        except (ValueError, TypeError):
            return False
    return True


def _array_to_range(lst: List[Any]) -> Any:
    """
    Convert a numeric list to ``{"min": …, "mean": …, "max": …}``.

    Non-finite elements (NaN / ±Inf strings) are excluded from the
    calculation.  If no finite elements remain the original list is
    returned unchanged so that no data is silently discarded.
    """
    finite = [f for v in lst if (f := _coerce_finite(v)) is not None]
    if not finite:
        return lst
    return {
        "min": min(finite),
        "mean": sum(finite) / len(finite),
        "max": max(finite),
    }


def _convert_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Walk a metadata dict and replace every value that is a numeric list
    (possibly containing non-finite string representations) with its range
    representation.  All other values are left untouched.
    """
    updated = {}
    for key, value in meta.items():
        if isinstance(value, list) and value and _is_numeric_list(value):
            updated[key] = _array_to_range(value)
        else:
            updated[key] = value
    return updated


def upgrade() -> None:
    """Convert numeric array metadata values to range dicts."""
    conn = op.get_bind()

    rows = conn.execute(
        text("SELECT id, metadata FROM simulations WHERE metadata IS NOT NULL")
    ).fetchall()

    for sim_id, metadata_raw in rows:
        # metadata_raw may already be a dict (PostgreSQL driver) or a JSON
        # string (SQLite / some PostgreSQL configurations).
        if isinstance(metadata_raw, str):
            try:
                meta = json.loads(metadata_raw)
            except (json.JSONDecodeError, TypeError):
                continue
        elif isinstance(metadata_raw, dict):
            meta = metadata_raw
        else:
            continue

        converted = _convert_metadata(meta)

        # Only write back if something actually changed
        if converted != meta:
            conn.execute(
                text(
                    "UPDATE simulations SET metadata = :metadata WHERE id = :sim_id"
                ),
                {
                    "metadata": json.dumps(converted),
                    "sim_id": sim_id,
                },
            )


def downgrade() -> None:
    """
    Convert range dicts back to plain numeric lists.

    Any metadata value that is a dict with exactly the keys ``min``, ``mean``
    and ``max`` is expanded back to a three-element list ``[min, mean, max]``.

    Note: this is a lossy reversal — the original array contents cannot be
    recovered, only the three summary statistics are preserved.
    """
    conn = op.get_bind()

    rows = conn.execute(
        text("SELECT id, metadata FROM simulations WHERE metadata IS NOT NULL")
    ).fetchall()

    for sim_id, metadata_raw in rows:
        if isinstance(metadata_raw, str):
            try:
                meta = json.loads(metadata_raw)
            except (json.JSONDecodeError, TypeError):
                continue
        elif isinstance(metadata_raw, dict):
            meta = metadata_raw
        else:
            continue

        reverted: Dict[str, Any] = {}
        changed = False
        for key, value in meta.items():
            if (
                isinstance(value, dict)
                and set(value.keys()) == {"min", "mean", "max"}
            ):
                reverted[key] = [value["min"], value["mean"], value["max"]]
                changed = True
            else:
                reverted[key] = value

        if changed:
            conn.execute(
                text(
                    "UPDATE simulations SET metadata = :metadata WHERE id = :sim_id"
                ),
                {
                    "metadata": json.dumps(reverted),
                    "sim_id": sim_id,
                },
            )
