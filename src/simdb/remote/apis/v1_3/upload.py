"""Server side of the IETF "Resumable Uploads for HTTP" protocol.

Implements draft-ietf-httpbis-resumable-upload-11 (interop version 8), the
counterpart to :mod:`simdb.cli.resumable_upload`. Uploaded bytes are staged into
the ``http`` partition (config ``partition.http``): a client uploading to
``/v1.3/upload/<simuuid>/<relpath>`` results in the file being written to
``<partition.http>/<simuuid>/<relpath>``. The simulation is then pushed
(metadata only) referencing those files with ``http:///<simuuid>/<relpath>``
URIs, which the existing ingestion pipeline resolves via the ``http`` partition.

Upload state lives on disk so it survives across worker processes: in-progress
bytes are written to ``<target>.partial`` and atomically renamed to ``<target>``
when the upload completes. The current offset is simply the size of that file.
"""

import contextlib
from pathlib import Path
from typing import Optional, Tuple

from flask import Response, request
from flask_restx import Namespace, Resource
from werkzeug.exceptions import Forbidden

from simdb.remote.core.auth import User, requires_auth
from simdb.remote.core.typing import current_app

api = Namespace("upload", path="/")

#: The draft interop version this server implements.
INTEROP_VERSION = "8"
INTEROP_HEADER = "Upload-Draft-Interop-Version"
PARTIAL_SUFFIX = ".partial"
#: Default maximum size of a single append (``PATCH``) body, advertised to
#: clients via the ``Upload-Limit`` header. Overridable with the
#: ``server.max_append_size`` config option.
DEFAULT_MAX_APPEND_SIZE = 8 * 1024 * 1024


def _max_append_size() -> int:
    value = current_app.simdb_config.get_option(
        "server.max_append_size", default=DEFAULT_MAX_APPEND_SIZE
    )
    try:
        return int(value)
    except (TypeError, ValueError):
        return DEFAULT_MAX_APPEND_SIZE


def _bool_field(value: bool) -> str:
    return "?1" if value else "?0"


def _parse_bool_field(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    value = value.strip()
    if value == "?1":
        return True
    if value == "?0":
        return False
    return None


def _partition_base() -> Path:
    base = current_app.simdb_config.get_string_option("partition.http", default=None)
    if not base:
        raise ValueError("Partition 'http' is not configured on the server")
    return Path(base).resolve()


def _resolve_target(target: str) -> Tuple[Path, Path]:
    """Resolve ``target`` to its ``(final, partial)`` paths within ``partition.http``.

    Raises ``ValueError`` if the resolved path would escape the partition.
    """
    base = _partition_base()
    final = (base / target).resolve()
    if not final.is_relative_to(base):
        raise Forbidden("Access denied.")
    partial = final.parent / (final.name + PARTIAL_SUFFIX)
    return final, partial


def _state(final: Path, partial: Path) -> Tuple[int, bool, bool]:
    """Return ``(offset, complete, exists)`` for the upload resource."""
    if partial.exists():
        return partial.stat().st_size, False, True
    if final.exists():
        return final.stat().st_size, True, True
    return 0, False, False


def _headers(offset: int, complete: bool) -> dict:
    return {
        INTEROP_HEADER: INTEROP_VERSION,
        "Upload-Offset": str(offset),
        "Upload-Complete": _bool_field(complete),
        # Advertise the server's append-size limit (structured-field dictionary)
        # so the client sizes its chunks accordingly.
        "Upload-Limit": f"max-append-size={_max_append_size()}",
        "Cache-Control": "no-store",
    }


@api.route("/upload/<path:target>")
class ResumableUpload(Resource):
    """A single resumable upload resource staged into the ``http`` partition."""

    @requires_auth()
    def post(self, target: str, user: User) -> Response:
        """Create (or reset) the upload resource and optionally write data."""
        final, partial = _resolve_target(target)
        partial.parent.mkdir(parents=True, exist_ok=True)

        data = request.get_data() or b""
        if len(data) > _max_append_size():
            return Response(status=413, headers=_headers(0, False))
        with partial.open("wb") as f:
            f.write(data)
        offset = len(data)

        complete = _parse_bool_field(request.headers.get("Upload-Complete")) or False
        if complete:
            partial.replace(final)

        headers = _headers(offset, complete)
        headers["Location"] = request.url
        return Response(status=201, headers=headers)

    @requires_auth()
    def head(self, target: str, user: User) -> Response:
        """Report the current offset / completeness of the upload resource."""
        final, partial = _resolve_target(target)
        offset, complete, exists = _state(final, partial)
        if not exists:
            return Response(status=404, headers={INTEROP_HEADER: INTEROP_VERSION})
        return Response(status=204, headers=_headers(offset, complete))

    @requires_auth()
    def patch(self, target: str, user: User) -> Response:
        """Append data to the upload resource at the given ``Upload-Offset``."""
        final, partial = _resolve_target(target)
        offset, complete, _exists = _state(final, partial)

        # Appending to an already-completed upload is a no-op when the client is
        # simply confirming completion at the final offset.
        if complete:
            return Response(status=200, headers=_headers(offset, True))

        try:
            requested_offset = int(request.headers.get("Upload-Offset", ""))
        except ValueError:
            return Response(status=400, headers={INTEROP_HEADER: INTEROP_VERSION})

        if requested_offset != offset:
            # Offset mismatch - tell the client our current offset so it resyncs.
            return Response(status=409, headers=_headers(offset, False))

        data = request.get_data() or b""
        if len(data) > _max_append_size():
            return Response(status=413, headers=_headers(offset, False))

        partial.parent.mkdir(parents=True, exist_ok=True)
        with partial.open("ab") as f:
            f.write(data)
        offset += len(data)

        request_complete = (
            _parse_bool_field(request.headers.get("Upload-Complete")) or False
        )
        if request_complete:
            partial.replace(final)
            return Response(status=200, headers=_headers(offset, True))

        return Response(status=204, headers=_headers(offset, False))

    @requires_auth()
    def delete(self, target: str, user: User) -> Response:
        """Cancel the upload and remove any staged data."""
        final, partial = _resolve_target(target)
        for path in (partial, final):
            with contextlib.suppress(FileNotFoundError):
                path.unlink()
        return Response(status=204, headers={INTEROP_HEADER: INTEROP_VERSION})
