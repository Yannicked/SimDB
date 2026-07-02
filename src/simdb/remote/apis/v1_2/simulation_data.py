"""IMAS simulation data endpoint: /data.

TODO: Temporary solution to retrieve data (for IBEX backend)
"""

from typing import Annotated, Any, NamedTuple, Optional

import imas
import numpy as np
from flask_restx import Namespace, Resource
from imas import IDSFactory
from imas.ids_convert import dd_version_map_from_factories
from imas.ids_defs import EMPTY_FLOAT
from imas.ids_path import IDSPath
from imas.ids_primitive import IDSPrimitive
from imas.ids_toplevel import IDSToplevel

from simdb.cli.manifest import DataObject
from simdb.database import DatabaseError
from simdb.imas.utils import (
    ImasError,
    open_imas,
)
from simdb.remote.core.auth import User, requires_auth
from simdb.remote.core.pydantic_utils import (
    Query,
    ResponseException,
    ServerException,
    pydantic_validate,
)
from simdb.remote.core.typing import current_app
from simdb.remote.models import ImasDataQueryParams, ImasDataResponse, QuantityData
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
                v != v or v == float("inf") or v == float("-inf") or v == EMPTY_FLOAT
            ):
                return None
            if isinstance(v, list):
                return [_clean(x) for x in v]
            return v

        return _clean(flat)
    return value


def _parse_ids_path(path: str) -> tuple:
    """Parse ``ids_name[:occurrence][/ids_path]`` into a 3-tuple"""
    head, _, ids_path = path.partition("/")
    if ":" in head:
        ids_name, occ_str = head.split(":", 1)
        try:
            occurrence = int(occ_str)
        except ValueError as exc:
            raise ValueError(
                f"Invalid occurrence in path '{path}': '{occ_str}'"
            ) from exc
    else:
        ids_name, occurrence = head, 0
    return ids_name, occurrence, ids_path


def _get_coordinates(node: IDSPrimitive, ids_name: str) -> list:
    """Return a :class:`QuantityData` for each coordinate dimension of *node*."""
    coords = []
    for i in range(node.metadata.ndim):
        coord = node.coordinates[i]
        if isinstance(coord, IDSPrimitive):
            data = (
                _to_python(coord.value)
                if coord.has_value
                else list(range(node.shape[i]))
            )
            coords.append(
                QuantityData(
                    name=f"{ids_name}/{coord._path}",
                    units=coord.metadata.units or "",
                    data=data,
                )
            )
        else:
            # Index-based coordinate: coord is already a numpy arange
            coords.append(
                QuantityData(
                    name=f"dim_{i + 1}",
                    units="",
                    data=coord.tolist(),
                )
            )
    return coords


def _resolve_renamed_ids_path(
    ids_obj: Any, ids_name: str, ids_path: str
) -> Optional[str]:
    """Return the stored DD path for a requested current-DD path, if renamed."""
    if not ids_path:
        return None

    stored_version = getattr(ids_obj, "_version", None) or getattr(
        ids_obj, "_dd_version", None
    )
    if not stored_version:
        return None

    ddmap, _source_is_older = dd_version_map_from_factories(
        ids_name,
        IDSFactory(stored_version),
        IDSFactory(),
    )
    return ddmap.new_to_old.path.get(ids_path)


def _copy_ids_properties(src_props: Any, dst_props: Any) -> None:
    """Copy all populated scalar fields from *src_props* to *dst_props*."""
    for field in src_props._children:
        src_node = getattr(src_props, field)
        if isinstance(src_node, IDSPrimitive) and src_node.has_value:
            getattr(dst_props, field).value = src_node.value


def _set_path_value(ids: IDSToplevel, node_path: Any, value: Any) -> None:
    """Generic function to write *value* into *ids* at *node_path* considering
    IDSStructArry.
    """
    p = IDSPath(str(node_path))
    current: Any = ids

    # allocate all intermediate nodes (structs and arrays) along the path
    for part, idx in zip(p.parts[:-1], p.indices[:-1]):
        child = getattr(current, part)
        if idx is not None:
            if len(child) <= idx:
                child.resize(idx + 1)
            current = child[idx]
        else:
            current = child
    # set the value at the leaf node, allocating array if needed
    last_part, last_idx = p.parts[-1], p.indices[-1]
    if last_idx is not None:
        child = getattr(current, last_part)
        if len(child) <= last_idx:
            child.resize(last_idx + 1)
        child[last_idx].value = value
    else:
        getattr(current, last_part).value = value


def _build_nonlazy_ids(
    lazy_ids: Any,
    ids_name: str,
    resolved_node: IDSPrimitive,
    stored_version: str,
) -> IDSToplevel:
    """Return a non-lazy IDS in *stored_version*"""
    nonlazy: IDSToplevel = IDSFactory(stored_version).new(ids_name)
    _copy_ids_properties(lazy_ids.ids_properties, nonlazy.ids_properties)
    _set_path_value(nonlazy, resolved_node._path, resolved_node.value)
    return nonlazy


def _get_ids_node(
    entry,
    ids_name: str,
    occurrence: int,
    ids_path: str,
    dd_version: "str | None" = None,
) -> IDSPrimitive:
    """Return the :class:`IDSPrimitive` leaf node at *ids_path* inside *ids_name*.

    Args:
        entry: Open IMAS data entry.
        ids_name: Name of the IDS to read.
        occurrence: Occurrence index of the IDS.
        ids_path: Slash-separated path within the IDS to the leaf node.
        dd_version: When provided, convert the field value to this DD
            version (e.g. ``"3.42.0"`` or ``"4.1.1"``) before returning.
    """
    ids_obj = entry.get(
        ids_name,
        occurrence,
        lazy=True,
        autoconvert=False,
        ignore_unknown_dd_version=True,
    )
    try:
        node = ids_obj[ids_path] if ids_path else ids_obj
    except (AttributeError, IndexError, KeyError) as exc:
        renamed_path = _resolve_renamed_ids_path(ids_obj, ids_name, ids_path)
        if not renamed_path:
            raise exc
        if dd_version is None:
            raise ValueError(
                f"Path '{ids_path}' does not exist in the stored DD version "
                f"({getattr(ids_obj, '_version', None) or getattr(ids_obj, '_dd_version', 'unknown')})"
                f" but is known under the name '{renamed_path}' in that version. "
                f"Pass dd_version to request an explicit DD conversion. "
                f"Original error: {type(exc).__name__}: {exc}"
            ) from exc
        try:
            node = ids_obj[renamed_path]
        except (AttributeError, IndexError, KeyError):
            raise exc from None

    if dd_version is not None:
        stored_version = (
            getattr(ids_obj, "_version", None)
            or getattr(ids_obj, "_dd_version", None)
            or entry.factory.version
        )
        minimal = _build_nonlazy_ids(ids_obj, ids_name, node, stored_version)
        converted = imas.convert_ids(minimal, dd_version)
        node = converted[ids_path] if ids_path else converted

    if not isinstance(node, IDSPrimitive):
        raise ValueError(
            f"path does not point to a scalar/array leaf "
            f"(reached {type(node).__name__}); add more path segments"
        )
    if not node.has_value:
        raise ValueError("field is not populated (no data written)")
    return node


class _SimulationImasFile(NamedTuple):
    simulation: Any
    imas_file: Any


def _get_simulation_and_imas_file(sim_id: str) -> _SimulationImasFile:
    try:
        simulation = current_app.db.get_simulation(sim_id)
    except DatabaseError as exc:
        raise ResponseException(str(exc), 404) from exc

    imas_outputs = [f for f in simulation.outputs if f.type == DataObject.Type.IMAS]
    if not imas_outputs:
        raise ResponseException(f"Simulation {sim_id} has no IMAS output files", 404)

    return _SimulationImasFile(simulation, imas_outputs[0])


# Endpoints


@api.route("/simulation/<path:sim_id>/data")
class SimulationImasData(Resource):
    @requires_auth()
    @pydantic_validate(api)
    def get(
        self,
        sim_id: str,
        user: User,
        params: Annotated[ImasDataQueryParams, Query()],
    ) -> ImasDataResponse:
        """Return the value at a given IDS path for a simulation's IMAS output."""
        result = _get_simulation_and_imas_file(sim_id)

        try:
            ids_name, occurrence, ids_path = _parse_ids_path(params.path)
        except ValueError as exc:
            raise ResponseException(str(exc)) from exc

        try:
            imas_uri = URI(str(result.imas_file.uri))
            if imas_uri.authority.host and "cache_mode" not in imas_uri.query:
                imas_uri.query.set("cache_mode", "none")
            entry = open_imas(imas_uri)
            with entry:
                node = _get_ids_node(
                    entry,
                    ids_name,
                    occurrence,
                    ids_path,
                    dd_version=params.dd_version,
                )
                coordinates = _get_coordinates(node, ids_name)
                field = QuantityData(
                    name=f"{ids_name}/{node._path}",
                    units=node.metadata.units or "",
                    data=_to_python(node.value),
                )
        except (ValueError, AttributeError, IndexError, KeyError) as exc:
            raise ResponseException(f"Invalid IDS path '{params.path}': {exc}") from exc
        except ImasError as exc:
            raise ServerException(f"Failed to open IMAS data: {exc}") from exc
        except Exception as exc:
            msg = str(exc)
            if "is empty" in msg or "not found" in msg.lower():
                raise ResponseException(msg, 404) from exc
            raise ServerException(msg) from exc

        return ImasDataResponse(
            simulation=str(result.simulation.uuid),
            path=params.path,
            occurrence=occurrence,
            field=field,
            coordinates=coordinates,
        )
