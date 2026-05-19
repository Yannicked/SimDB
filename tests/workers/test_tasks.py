from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
from uuid import uuid1

import pytest

from simdb.config import Config
from simdb.enums import IngestionStatus
from simdb.remote.models import FileData
from simdb.uri import URI, URIParserError
from simdb.workers.tasks import (
    _calculate_checksum,
    _copy_files,
    _create_file_from_data,
    _get_imas_identifier_path,
    _imas_path_to_uri,
    _resolve_paths,
    _resolve_uri_to_path,
    copy_files_task,
)


def test_calculate_checksum_returns_hex_string(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")

    result = _calculate_checksum(test_file)

    assert isinstance(result, str)
    assert len(result) == 40


def test_calculate_checksum_content_independent(tmp_path):
    file1 = tmp_path / "file1.txt"
    file1.write_text("hello world")
    file2 = tmp_path / "file2.txt"
    file2.write_text("hello world")

    checksum1 = _calculate_checksum(file1)
    checksum2 = _calculate_checksum(file2)

    assert checksum1 == checksum2


def test_calculate_checksum_different_content(tmp_path):
    file1 = tmp_path / "file1.txt"
    file1.write_text("hello")
    file2 = tmp_path / "file2.txt"
    file2.write_text("world")

    checksum1 = _calculate_checksum(file1)
    checksum2 = _calculate_checksum(file2)

    assert checksum1 != checksum2


def test_calculate_checksum_binary_file(tmp_path):
    test_file = tmp_path / "binary.bin"
    test_file.write_bytes(b"\x00\x01\x02\x03")

    result = _calculate_checksum(test_file)

    assert isinstance(result, str)
    assert len(result) == 40


def test_get_imas_identifier_path_netcdf_returns_self(tmp_path):
    nc_file = tmp_path / "data.nc"
    nc_file.touch()

    result = _get_imas_identifier_path(nc_file)

    assert result == nc_file


def test_get_imas_identifier_path_directory_returns_parent(tmp_path):
    ids_dir = tmp_path / "ids_dir"
    ids_dir.mkdir()

    result = _get_imas_identifier_path(ids_dir)

    assert result == ids_dir.parent


def test_imas_path_to_uri_netcdf_returns_file_scheme(tmp_path):
    nc_file = tmp_path / "data.nc"
    nc_file.touch()

    uri = _imas_path_to_uri(nc_file)

    assert uri.scheme == "file"
    assert uri.path == nc_file


def test_imas_path_to_uri_single_ids_child_returns_imas_ascii(tmp_path):
    ids_dir = tmp_path / "ids_dir"
    ids_dir.mkdir()
    ids_file = ids_dir / "child.ids"
    ids_file.touch()

    uri = _imas_path_to_uri(ids_dir)

    assert uri.scheme == "imas"
    assert uri.path == Path("ascii")
    assert uri.query.get("path") == str(ids_dir)


def test_imas_path_to_uri_h5_children_returns_imas_hdf5(tmp_path):
    ids_dir = tmp_path / "ids_dir"
    ids_dir.mkdir()
    (ids_dir / "file1.h5").touch()
    (ids_dir / "file2.h5").touch()

    uri = _imas_path_to_uri(ids_dir)

    assert uri.scheme == "imas"
    assert str(uri.path) == "hdf5"


def test_imas_path_to_uri_mdsplus_tree_returns_imas_mdsplus(tmp_path):
    ids_dir = tmp_path / "ids_dir"
    ids_dir.mkdir()
    (ids_dir / "ids_001.tree").touch()
    (ids_dir / "ids_001.characteristics").touch()
    (ids_dir / "ids_001.datafile").touch()

    uri = _imas_path_to_uri(ids_dir)

    assert uri.scheme == "imas"
    assert str(uri.path) == "mdsplus"


def test_imas_path_to_uri_unknown_raises_error(tmp_path):
    ids_dir = tmp_path / "ids_dir"
    ids_dir.mkdir()
    (ids_dir / "file1.txt").touch()

    with pytest.raises(ValueError, match="IMAS backend could not be identified"):
        _imas_path_to_uri(ids_dir)


@pytest.fixture
def config_with_partition(tmp_path):
    config = Config()
    partition_path = tmp_path / "partition_data"
    partition_path.mkdir()
    config.set_option("partition.data", str(partition_path))
    return config, partition_path


def test_resolve_uri_to_path_resolves_valid_uri(config_with_partition):
    config, partition_path = config_with_partition
    uri = URI(scheme="data", path="/subdir/file.txt")

    result = _resolve_uri_to_path(uri, config)

    assert result == partition_path / "subdir" / "file.txt"


def test_resolve_uri_to_path_missing_partition_raises_error():
    config = Config()
    uri = URI(scheme="unknown", path="/file.txt")

    with pytest.raises(ValueError, match="Partition 'unknown' not found"):
        _resolve_uri_to_path(uri, config)


def test_resolve_uri_to_path_empty_scheme_raises_error():
    config = Config()

    with pytest.raises(URIParserError):
        uri = URI(scheme=None, path="/path/without/scheme")
        _resolve_uri_to_path(uri, config)


def test_resolve_paths_resolves_multiple_files(config_with_partition):
    config, partition_path = config_with_partition
    file1 = FileData(
        type="FILE",
        uri="data:/file1.txt",
        checksum="abc",
        datetime=datetime.now(timezone.utc),
    )
    file2 = FileData(
        type="FILE",
        uri="data:/file2.txt",
        checksum="def",
        datetime=datetime.now(timezone.utc),
    )

    result = _resolve_paths([file1, file2], config)

    assert result == [partition_path / "file1.txt", partition_path / "file2.txt"]


def test_copy_files_copies_single_file(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("content")
    common_root = tmp_path
    dst_basepath = tmp_path / "dest"

    _copy_files([source], common_root, dst_basepath)

    assert (dst_basepath / "source.txt").exists()
    assert (dst_basepath / "source.txt").read_text() == "content"


def test_copy_files_preserves_relative_path(tmp_path):
    source_dir = tmp_path / "source" / "subdir"
    source_dir.mkdir(parents=True)
    source = source_dir / "file.txt"
    source.write_text("content")
    common_root = tmp_path / "source"
    dst_basepath = tmp_path / "dest"

    _copy_files([source], common_root, dst_basepath)

    assert (dst_basepath / "subdir" / "file.txt").exists()


def test_copy_files_copies_multiple_files(tmp_path):
    source1 = tmp_path / "file1.txt"
    source1.write_text("content1")
    source2 = tmp_path / "file2.txt"
    source2.write_text("content2")
    common_root = tmp_path
    dst_basepath = tmp_path / "dest"

    _copy_files([source1, source2], common_root, dst_basepath)

    assert (dst_basepath / "file1.txt").exists()
    assert (dst_basepath / "file2.txt").exists()


def test_copy_files_creates_destination_directories(tmp_path):
    source = tmp_path / "source" / "nested" / "file.txt"
    source.parent.mkdir(parents=True)
    source.write_text("content")
    common_root = tmp_path / "source"
    dst_basepath = tmp_path / "dest"

    _copy_files([source], common_root, dst_basepath)

    assert (dst_basepath / "nested" / "file.txt").exists()


def test_copy_files_preserves_permissions(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("content")
    source.chmod(0o755)
    common_root = tmp_path
    dst_basepath = tmp_path / "dest"

    _copy_files([source], common_root, dst_basepath)

    assert (dst_basepath / "source.txt").exists()


@pytest.fixture
def config_with_file_and_partition(tmp_path):
    config = Config()
    partition_path = tmp_path / "partition_data"
    partition_path.mkdir()
    config.set_option("partition.data", str(partition_path))
    data_file = partition_path / "testfile.txt"
    data_file.write_text("content")
    return config, partition_path, data_file


def test_create_file_from_data_raises_on_checksum_mismatch(
    config_with_file_and_partition,
):
    config, _partition_path, data_file = config_with_file_and_partition
    file_data = FileData(
        type="FILE",
        uri="data:testfile.txt",
        checksum="wrong_checksum",
        datetime=datetime.now(timezone.utc),
    )

    with pytest.raises(ValueError, match="Hash of file does not match"):
        _create_file_from_data(file_data, config, data_file)


@pytest.fixture
def mock_config_and_db(tmp_path):
    config = Config()
    db_file = tmp_path / "test.db"
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    partition_dir = tmp_path / "partition"
    partition_dir.mkdir()

    config.set_option("database.type", "sqlite")
    config.set_option("database.file", str(db_file))
    config.set_option("server.upload_folder", str(upload_dir))
    config.set_option("partition.data", str(partition_dir))

    source_file = partition_dir / "source.txt"
    source_file.write_text("test content")

    return config, upload_dir, partition_dir


@mock.patch("simdb.workers.tasks.get_db")
@mock.patch("simdb.workers.tasks.Config")
def test_copy_files_task_creates_file_records(
    mock_config_class, mock_get_db, mock_config_and_db
):
    config, _upload_dir, partition_dir = mock_config_and_db
    mock_config_class.return_value = config

    simulation_uuid = uuid1()
    source_file = partition_dir / "source.txt"
    checksum = _calculate_checksum(source_file)
    input_files = [
        FileData(
            type="FILE",
            uri=f"data:/{source_file.name}",
            checksum=checksum,
            datetime=datetime.now(timezone.utc),
        )
    ]

    mock_db = mock.MagicMock()
    mock_simulation = mock.MagicMock()
    mock_simulation.uuid = simulation_uuid
    mock_simulation.inputs = []
    mock_simulation.outputs = []
    mock_db.get_simulation.return_value = mock_simulation
    mock_get_db.return_value = mock_db

    copy_files_task(simulation_uuid, input_files, [])

    mock_db.session.add.assert_called()
    assert mock_simulation.ingestion_status == IngestionStatus.COPIED


@mock.patch("simdb.workers.tasks.get_db")
@mock.patch("simdb.workers.tasks.Config")
def test_copy_files_task_copies_files_to_upload_folder(
    mock_config_class, mock_get_db, mock_config_and_db
):
    config, upload_dir, partition_dir = mock_config_and_db
    mock_config_class.return_value = config

    simulation_uuid = uuid1()
    source_file = partition_dir / "source.txt"
    checksum = _calculate_checksum(source_file)
    input_files = [
        FileData(
            type="FILE",
            uri=f"data:{source_file.name}",
            checksum=checksum,
            datetime=datetime.now(timezone.utc),
        )
    ]

    mock_db = mock.MagicMock()
    mock_simulation = mock.MagicMock()
    mock_simulation.uuid = simulation_uuid
    mock_simulation.inputs = []
    mock_simulation.outputs = []
    mock_db.get_simulation.return_value = mock_simulation
    mock_get_db.return_value = mock_db

    copy_files_task(simulation_uuid, input_files, [])

    expected_destination = upload_dir / simulation_uuid.hex / "source.txt"
    assert expected_destination.exists()
    assert expected_destination.read_text() == "test content"


@mock.patch("simdb.workers.tasks.get_db")
@mock.patch("simdb.workers.tasks.Config")
def test_copy_files_task_with_empty_inputs(
    mock_config_class, mock_get_db, mock_config_and_db
):
    config, _upload_dir, _partition_dir = mock_config_and_db
    mock_config_class.return_value = config

    simulation_uuid = uuid1()

    mock_db = mock.MagicMock()
    mock_simulation = mock.MagicMock()
    mock_simulation.uuid = simulation_uuid
    mock_simulation.inputs = []
    mock_simulation.outputs = []
    mock_db.get_simulation.return_value = mock_simulation
    mock_get_db.return_value = mock_db

    copy_files_task(simulation_uuid, [], [])

    assert mock_simulation.ingestion_status == IngestionStatus.COPIED
