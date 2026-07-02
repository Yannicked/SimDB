"""IMAS simulation data endpoint: /data.

TODO: Temporary solution to retrieve data (for IBEX backend)
"""

from typing import Annotated, Any, NamedTuple

import imas
import numpy as np
from flask_restx import Namespace, Resource
from imas.ids_defs import EMPTY_FLOAT
from imas.ids_primitive import IDSPrimitive

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


def _get_ids_node(
    entry,
    ids_name: str,
    occurrence: int,
    ids_path: str,
    autoconvert: bool = False,
    dd_convert: bool = False,
    dd_target_version: "str | None" = None,
) -> IDSPrimitive:
    """Return the :class:`IDSPrimitive` leaf node at *ids_path* inside *ids_name*.

    Args:
        entry: Open IMAS data entry.
        ids_name: Name of the IDS to read.
        occurrence: Occurrence index of the IDS.
        ids_path: Slash-separated path within the IDS to the leaf node.
        autoconvert: Passed to :meth:`~imas.DBEntry.get`.  When ``True`` IMAS
            automatically applies NBC path remapping at read time, returning
            the IDS in the entry's factory version.  Useful when the stored
            and factory versions share the same major version (e.g. both
            3.x).  Defaults to ``False`` so data is returned in its stored
            DD version.
        dd_convert: When ``True``, explicitly convert the IDS using
            :func:`imas.convert_ids` after reading.  The target version is
            *dd_target_version* when given, otherwise the entry's factory
            version.
        dd_target_version: Target DD version string (e.g. ``"3.42.0"``)
            for :func:`imas.convert_ids`.  Only used when *dd_convert* is
            ``True``.  Falls back to ``entry.factory.version`` when ``None``.
    """
    ids_obj = entry.get(
        ids_name,
        occurrence,
        lazy=not dd_convert,
        autoconvert=autoconvert,
        ignore_unknown_dd_version=True,
    )
    if dd_convert:
        target_version = dd_target_version or entry.factory.version
        ids_obj = imas.convert_ids(ids_obj, target_version)
    node = ids_obj[ids_path] if ids_path else ids_obj
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
                    autoconvert=params.autoconvert,
                    dd_convert=params.dd_convert,
                    dd_target_version=params.dd_target_version,
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
