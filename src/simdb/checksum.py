import hashlib
from enum import Enum
from pathlib import Path
from typing import Iterable, List, Optional

from simdb.imas.utils import imas_files

from .uri import URI

CHUNK_SIZE = 2**20


class ChecksumAlgo(str, Enum):
    sha1 = "sha1"
    sha256 = "sha256"

    unknown = "unknown"


DEFAULT_CHECKSUM_ALGO = ChecksumAlgo.sha1


def checksum_files(paths: Iterable[Path], algo=DEFAULT_CHECKSUM_ALGO):
    hash_object = hashlib.new(algo)

    for path in sorted(paths):
        if not path.exists():
            raise ValueError("File does not exist")
        if not path.is_file():
            raise ValueError("File appears to be a directory")
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(CHUNK_SIZE), b""):
                hash_object.update(chunk)

    return hash_object.hexdigest()


def checksum(uri: URI, ids_list: Optional[List[str]] = None):
    if uri.scheme == "file" and uri.path is not None:
        return checksum_files([uri.path])
    if uri.scheme == "imas":
        return checksum_files(imas_files(uri, ids_list))
