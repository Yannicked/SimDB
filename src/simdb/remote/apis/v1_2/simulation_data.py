"""Simulation IMAS data endpoint: /data.

TODO: Temporal solution to retrive data (Use IBEX backend)
"""

import re
import uuid as _uuid
from typing import Any

import numpy as np
from flask import request
from flask_restx import Namespace, Resource
from imas.ids_primitive import IDSPrimitive

from simdb.cli.manifest import DataObject
from simdb.database import DatabaseError
from simdb.imas.utils import FLOAT_MISSING_VALUE, INT_MISSING_VALUE, ImasError, open_imas
from simdb.remote.core.auth import User, requires_auth
from simdb.remote.core.cache import cache
from simdb.remote.core.typing import current_app
from simdb.uri import URI

api = Namespace("data", path="/")


# Helpers


def _to_python(value: Any) -> Any:
    """Convert a value returned by IDSPrimitive.value to a JSON-serialisable
    Python object."""
    if isinstance(value, np.ndarray):
        flat = value.tolist()

        def _clean(v):
            if isinstance(v, float) and (
                v != v or v == float("inf") or v == float("-inf") or v == FLOAT_MISSING_VALUE
            ):
                return None
            if isinstance(v, list):
                return [_clean(x) for x in v]
            return v

        return _clean(flat)
    if isinstance(value, np.integer):
        v = int(value)
        return None if v == INT_MISSING_VALUE else v
    if isinstance(value, np.floating):
        v = float(value)
        return None if (np.isnan(v) or np.isinf(v) or v == FLOAT_MISSING_VALUE) else v
    if isinstance(value, np.complexfloating):
        return {"real": float(value.real), "imag": float(value.imag)}
    if isinstance(value, np.bool_):
        return bool(value)
    return value

# TODO Replace this logic with slicing when supported by imas-python.
# TODO Add support for [:], [:-1], and [2:4:2] python slicing syntax.
def _traverse_path(entry, ids_name: str, field_segments: list, occurrence: int):
    """Walk *field_segments* inside *ids_name* and return (value, shape, coordinate_path).

    Each segment is either:
    - a non-negative integer string → array-of-structures index
    - a plain name → attribute access (IDSStructure child node)
    """
    ids_obj = entry.get(
        ids_name, occurrence,
        lazy=True, autoconvert=False, ignore_unknown_dd_version=True,
    )
    node = ids_obj
    for segment in field_segments:
        if segment.isdigit():
            node = node[int(segment)]
        else:
            try:
                node = getattr(node, segment)
            except AttributeError:
                raise ValueError(f"segment '{segment}' not found in IDS path")
    if not isinstance(node, IDSPrimitive):
        raise ValueError(
            f"path does not point to a scalar/array leaf "
            f"(reached {type(node).__name__}); add more path segments"
        )
    if not node.has_value:
        raise ValueError(f"field is not populated (no data written)")

    node_shape = list(node.shape) if node.metadata.ndim > 0 else None

    coordinate_path = None
    try:
        def _replace_placeholder(m, _segs=field_segments):
            idx = next((s for s in _segs if s.isdigit()), "0")
            return "/" + idx + "/"

        for coord in node.metadata.coordinates:
            clean = re.sub(r"\([^)]+\)/", _replace_placeholder, str(coord))
            coordinate_path = ids_name + "/" + clean
            break
    except Exception:
        pass

    return _to_python(node.value), node_shape, coordinate_path


def _fetch_field(uri_str: str, ids_name: str, field_segments: tuple, occurrence: int) -> tuple:
    """Open the IMAS entry, traverse the path, and return (value, shape, coordinate_path).

    Scalar results (``shape is None``) are written into the response cache so
    that repeated requests skip the IMAS open.  Array values are intentionally
    *not* cached: caching large numpy-derived lists would create persistent
    memory pressure and could fill the cache backend with multi-MB payloads.
    """
    if ids_name and not field_segments:  # bare IDS name only – no leaf, skip cache probe
        pass
    else:
        cache_key = (
            f"simdb:field:{uri_str}:{ids_name}:"
            f"{'/' .join(field_segments)}:{occurrence}"
        )
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    entry = open_imas(URI(uri_str))
    with entry:
        result = _traverse_path(entry, ids_name, list(field_segments), occurrence)

    _value, shape, _coord = result
    if shape is None:  # scalar leaf – safe to persist in cache
        cache.set(cache_key, result)  # type: ignore[possibly-undefined]
    return result


def _get_simulation_and_imas_file(sim_id: str, file_uuid_str: str | None):
    try:
        simulation = current_app.db.get_simulation(sim_id)
    except DatabaseError as exc:
        return None, None, ({"error": str(exc)}, 404)

    imas_outputs = [f for f in simulation.outputs if f.type == DataObject.Type.IMAS]
    if not imas_outputs:
        return None, None, (
            {"error": f"Simulation {sim_id} has no IMAS output files"}, 404
        )

    if not file_uuid_str:
        return simulation, imas_outputs[0], None

    try:
        target_uuid = _uuid.UUID(file_uuid_str)
    except ValueError:
        return None, None, ({"error": f"Invalid file_uuid: {file_uuid_str!r}"}, 400)

    imas_file = next((f for f in imas_outputs if f.uuid == target_uuid), None)
    if imas_file is None:
        return None, None, ({"error": f"File {file_uuid_str} not found"}, 404)

    return simulation, imas_file, None


# Endpoints

@api.route("/simulation/<path:sim_id>/data")
class SimulationImasData(Resource):
    @requires_auth()
    def get(self, sim_id: str, user: User):
        """Return the value at a given IDS path for a simulation's IMAS output.

        Query parameters
        ----------------
        path       (required) IDS path, e.g. ``core_profiles/profiles_1d/0/electrons/density``
        file_uuid  (optional) UUID of an IMAS output file
        occurrence (optional) IDS occurrence index (default 0)
        """
        path = request.args.get("path", "").strip()
        if not path:
            return {"error": "Query parameter 'path' is required"}, 400

        file_uuid_str = request.args.get("file_uuid", "").strip() or None

        try:
            occurrence = int(request.args.get("occurrence", "0"))
        except ValueError:
            return {"error": "'occurrence' must be a non-negative integer"}, 400
        if occurrence < 0:
            return {"error": "'occurrence' must be a non-negative integer"}, 400

        simulation, imas_file, error = _get_simulation_and_imas_file(
            sim_id, file_uuid_str
        )
        if error:
            payload, status = error
            if file_uuid_str and status == 404 and "File " in payload["error"]:
                return (
                    {
                        "error": (
                            f"File {file_uuid_str} not found or is not an IMAS "
                            "output for this simulation"
                        )
                    },
                    404,
                )
            return payload, status

        segments = [s for s in path.split("/") if s]
        if not segments:
            return {"error": "'path' must not be empty"}, 400

        ids_name = segments[0]
        field_segments = segments[1:]

        try:
            value, shape, coordinate_path = _fetch_field(
                str(imas_file.uri), ids_name, tuple(field_segments), occurrence
            )
        except (ValueError, AttributeError, IndexError, KeyError) as exc:
            return {"error": f"Invalid IDS path '{path}': {exc}"}, 400
        except (ImasError,) as exc:
            return {"error": f"Failed to open IMAS data: {exc}"}, 500
        except Exception as exc:
            msg = str(exc)
            status = 404 if "is empty" in msg or "not found" in msg.lower() else 500
            return {"error": msg}, status

        return {
            "simulation": str(simulation.uuid),
            "file_uuid": str(imas_file.uuid),
            "path": path,
            "occurrence": occurrence,
            "value": value,
            "shape": shape,
            "coordinate": coordinate_path,
        }
