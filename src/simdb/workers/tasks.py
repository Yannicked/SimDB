from ty_extensions import Unknown
import os
import hashlib
import logging
import shutil
from pathlib import Path
from typing import List
from uuid import UUID

from simdb.config import Config
from simdb.database.database import get_db
from simdb.email.server import EmailServer
from simdb.remote.models import FileData
from simdb.uri import URI

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
def copy_files_task(simulation_uuid: UUID, files_to_copy: list[FileData]):
    """
    1. verify files
    2. copy files
    3. update database
    """
    config = Config()
    config.load()
    database = get_db(config)

    # Check this before task start
    # Should map: sdcc:///my_path to /sdcc/mount/my_path
    # and:        http:///uuid to /http/staging/area/uuid
    uris = (URI(file.uri) for file in files_to_copy)
    file_uuids = (file.uuid for file in files_to_copy)
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

    # Calculate checksums
    hash_algo = "sha256"
    chunk_size = 8129
    for path, file_obj in zip(paths, files_to_copy):
        hash_obj = hashlib.new(hash_algo)
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_obj.update(chunk)
        hash = hash_obj.hexdigest()
        if file_obj.checksum != hash:
            raise ValueError("Hash of file does not match provided checksum")
    
    common_root = os.path.commonpath(paths)
    dst_basepath = (
        Path(config.get_string_option("server.upload_folder")) / simulation_uuid.hex
    )
    dst_paths: list[Path] = []
    for path in paths:
        dst_paths.append(dst_basepath / path.relative_to(common_root))

    simulation = database.get_simulation(simulation_uuid.hex)
    simulation.ingestion_status = simulation.IngestionStatus.COPYING
    database.session.commit()

    for source, destination in zip(paths, dst_paths):
        destination.parent.mkdir(exist_ok=True, parents=True)
        shutil.copy2(source, destination)

    for destination, file_obj in zip(dst_paths, files_to_copy):
        if file_obj.type != "IMAS":
            continue
        
        
    
    simulation = database.get_simulation(simulation_uuid.hex)
    simulation.ingestion_status = simulation.IngestionStatus.COPIED
    database.session.commit()
    database.close()
