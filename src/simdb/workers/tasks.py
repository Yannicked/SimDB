import hashlib
import itertools
import logging
import os
import shutil
from pathlib import Path
from typing import Iterable, List
from uuid import UUID

from simdb.config import Config
from simdb.database.database import get_db
from simdb.database.models import File
from simdb.email.server import EmailServer
from simdb.enums import IngestionStatus
from simdb.remote.models import FileData, FileDataList
from simdb.uri import URI
from simdb.workers.celery import celery_app

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


def _imas_path_to_uri(imas_path: Path) -> URI:
    if imas_path.suffix == ".nc":
        return URI(scheme="file", path=imas_path)

    children = set(imas_path.iterdir())

    if any(child.suffix == ".ids" for child in children):
        u = URI(scheme="imas", path="ascii")
        u.query.set("path", str(imas_path))
        return u

    if any(child.suffix == ".h5" for child in children) and any(
        child.name == "master.h5" for child in children
    ):
        u = URI(scheme="imas", path="hdf5")
        u.query.set("path", str(imas_path))
        return u

    if {p.name for p in children} >= {
        "ids_001.tree",
        "ids_001.characteristics",
        "ids_001.datafile",
    }:
        u = URI(scheme="imas", path="mdsplus")
        u.query.set("path", str(imas_path))
        return u

    raise ValueError("IMAS backend could not be identified.")


def _resolve_uri_to_path(uri: URI, config: Config) -> Path:
    partition = uri.scheme
    if not partition:
        raise ValueError("Partition not given")
    partition_path_str = config.get_string_option(
        f"partition.{partition}", default=None
    )
    if not partition_path_str:
        raise ValueError(f"Partition '{partition}' not found in config")
    partition_path = Path(partition_path_str)
    path = uri.path
    if not path:
        raise ValueError("Path not given")
    path = path.relative_to(path.anchor)
    target = (partition_path / path).resolve()
    if not target.is_relative_to(partition_path):
        raise ValueError("Access denied.")
    return target


def _resolve_paths(files_data: list[FileData], config: Config) -> list[Path]:
    return [_resolve_uri_to_path(URI(f.uri), config) for f in files_data]


def _resolve_destination_path(source: Path, common_root: Path, dst_basepath: Path):
    return dst_basepath / source.relative_to(common_root)


def _copy_files(
    paths: Iterable[Path],
    common_root: Path,
    dst_basepath: Path,
):
    for source in paths:
        destination = _resolve_destination_path(source, common_root, dst_basepath)
        destination.parent.mkdir(exist_ok=True, parents=True)
        shutil.copy2(source, destination)


def _calculate_checksum(path: Path) -> str:
    sha1 = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha1.update(chunk)
    return sha1.hexdigest()


def _get_imas_identifier_path(path: Path) -> Path:
    if path.suffix == ".nc":
        return path
    return path.parent


def _create_file_from_data(
    data: FileData, config: Config, imas_identifier_path: Path
) -> File:
    uri = URI(data.uri)
    path = _resolve_uri_to_path(uri, config)

    checksum = _calculate_checksum(path)
    if data.checksum != checksum:
        raise ValueError("Hash of file does not match provided checksum")

    file = File.from_data_model(data)
    file.uri = _imas_path_to_uri(imas_identifier_path)

    return file


def _create_files_from_data_list(
    files_data: list[FileData], config: Config, common_root: Path, dst_basepath: Path
) -> list[File]:
    seen_imas_paths: set[Path] = set()
    files: list[File] = []

    for file_data in files_data:
        uri = URI(file_data.uri)
        path = _resolve_destination_path(
            _resolve_uri_to_path(uri, config), common_root, dst_basepath
        )

        if file_data.type == "IMAS":
            imas_path = _get_imas_identifier_path(path)
            if imas_path in seen_imas_paths:
                continue
            seen_imas_paths.add(imas_path)
            file = _create_file_from_data(file_data, config, imas_path)
        else:
            checksum = _calculate_checksum(path)
            if file_data.checksum != checksum:
                raise ValueError("Hash of file does not match provided checksum")
            file = File.from_data_model(file_data)
            file.uri = URI(scheme="file", path=path)

        files.append(file)

    return files


@celery_app.task
def copy_files_task(
    simulation_uuid: UUID,
    input_files_d: list[FileData],
    output_files_d: list[FileData],
):
    input_files = FileDataList.model_validate(input_files_d).root
    output_files = FileDataList.model_validate(output_files_d).root
    config = Config()
    config.load()
    database = get_db(config)

    simulation = database.get_simulation(simulation_uuid.hex)
    simulation.ingestion_status = IngestionStatus.COPYING
    database.session.commit()

    try:
        input_paths = _resolve_paths(input_files, config)
        output_paths = _resolve_paths(output_files, config)
        paths = set(input_paths + output_paths)
        if len(paths) == 0:
            common_root = Path()
        elif len(paths) == 1:
            common_root = next(iter(paths)).parent
        else:
            common_root = Path(os.path.commonpath(paths))
        dst_basepath: Path = (
            Path(config.get_string_option("server.upload_folder")) / simulation_uuid.hex
        )

        _copy_files(paths, common_root, dst_basepath)

        inputs = _create_files_from_data_list(
            input_files, config, common_root, dst_basepath
        )
        outputs = _create_files_from_data_list(
            output_files, config, common_root, dst_basepath
        )

        for f in [*inputs, *outputs]:
            database.session.add(f)

        simulation.inputs = inputs
        simulation.outputs = outputs
        simulation.ingestion_status = IngestionStatus.COPIED
        database.session.commit()
    except Exception:
        simulation.ingestion_status = IngestionStatus.COPY_FAILED
        database.session.commit()
        raise
    finally:
        database.close()


@celery_app.task
def validate_imas_task(simulation_uuid: UUID):
    config = Config()
    config.load()
    database = get_db(config)

    simulation = database.get_simulation(simulation_uuid.hex)
    simulation.ingestion_status = IngestionStatus.VALIDATING
    database.session.commit()

    for _file in itertools.chain(simulation.inputs, simulation.outputs):
        # TODO
        pass

    simulation.ingestion_status = IngestionStatus.VALIDATED
    database.session.commit()
    database.close()


@celery_app.task
def complete_ingestion_task(simulation_uuid: UUID):
    config = Config()
    config.load()
    database = get_db(config)

    simulation = database.get_simulation(simulation_uuid.hex)
    simulation.ingestion_status = IngestionStatus.COMPLETED
    database.session.commit()
