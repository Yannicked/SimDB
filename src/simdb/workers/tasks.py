import hashlib
from ty_extensions import Unknown
from simdb.database.database import get_db
import shutil
from uuid import UUID
from pathlib import Path
from simdb.uri import URI
from simdb.remote.models import FileData, FileDataList
import logging
from typing import List, Optional

from simdb.config import Config
from simdb.email.server import EmailServer

from .celery import celery_app

logger = logging.getLogger(__name__)


@celery_app.task
def send_email_task(
    subject: str,
    body: str,
    to_addresses: List[str],
) -> dict:
    config = Config()
    config.load()

    email_server = EmailServer(config)
    email_server.send_message(subject, body, to_addresses)

    return {
        "status": "sent",
        "subject": subject,
        "recipients": to_addresses,
    }


@celery_app.task
def copy_files_task(simulation_uuid: UUID, files_to_copy: FileDataList):
    """
    1. verify files
    2. copy files
    3. update database
    """
    config = Config()
    config.load()

    # Check this before task start
    # Should map: sdcc:///my_path to /sdcc/mount/my_path
    # and:        http:///uuid to /http/staging/area/uuid
    uris = (URI(file.uri) for file in files_to_copy.root)
    file_uuids = (file.uuid for file in files_to_copy.root)
    paths: list[Path] = []
    for uri in uris:
        partition = uri.scheme
        if not partition:
            raise ValueError("Partition not given")
        partition_path_str = config.get_string_option(
            f"partition.{partition}", default=None
        )
        if not partition_path_str:
            raise ValueError("Partition not found in config")
        partition_path = Path(partition_path_str)

        path = uri.path
        if not path:
            raise ValueError("Path not given")

        paths.append(partition_path / path)

    hash_algo = "sha256"
    chunk_size = 8129
    for (path, file_obj) in zip(paths, files_to_copy.root):
        hash_obj = hashlib.new(hash_algo)
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                hash_obj.update(chunk)
        hash = hash_obj.hexdigest()
        if file_obj.checksum != hash:
            raise ValueError("Hash of file does not match provided checksum")

    dst_basepath = (
        Path(config.get_string_option("server.upload_folder")) / simulation_uuid.hex
    )
    dst_paths = []
    for uuid in file_uuids:
        dst_paths.append(dst_basepath / uuid.hex)

    for source, destination in zip(paths, dst_paths):
        shutil.copy2(source, destination)

    database = get_db(config)
    simulation = database.get_simulation(simulation_uuid.hex)