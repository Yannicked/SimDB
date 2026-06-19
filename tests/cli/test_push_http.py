"""Tests for the HTTP push client helpers and CLI command."""

import hashlib
import uuid
from datetime import datetime, timezone
from unittest import mock

from click.testing import CliRunner
from utils import config_test_file

from simdb.cli.remote_api import _compute_checksums, _expand_directories_http
from simdb.cli.simdb import cli
from simdb.imas.utils import SimDBUrl
from simdb.remote.models import FileData


def _file_data(path) -> FileData:
    return FileData(
        type="FILE",
        uri=SimDBUrl.build(scheme="file", path=str(path), host="").encoded_string(),
        checksum="ignored",
        datetime=datetime.now(timezone.utc),
    )


def test_expand_directories_http_uses_partition_relative_paths(tmp_path):
    # Files under a configured partition keep their partition-relative layout,
    # namespaced under <uuid>/<partition>/ (mirrors local push mapping).
    partition = tmp_path / "data"
    (partition / "subdir").mkdir(parents=True)
    f = partition / "subdir" / "file.txt"
    f.write_text("hello")
    sim_uuid = uuid.uuid4()
    partitions = {"data": str(partition)}

    result = _expand_directories_http([_file_data(f)], sim_uuid, partitions)

    assert len(result) == 1
    file_data, local_path, target = result[0]
    assert local_path == f
    assert target == f"{sim_uuid.hex}/data/subdir/file.txt"
    parsed = SimDBUrl(file_data.uri)
    assert parsed.scheme == "http"
    assert parsed.host == sim_uuid.hex
    assert parsed.path == "/data/subdir/file.txt"
    assert file_data.type == "FILE"
    assert file_data.checksum == ""


def test_compute_checksums_populates_sha1(tmp_path):
    f1 = tmp_path / "a.txt"
    f1.write_bytes(b"hello")
    f2 = tmp_path / "b.txt"
    f2.write_bytes(b"world!!")

    fd1 = _file_data(f1)
    fd2 = _file_data(f2)
    files = [(fd1, f1, "a"), (fd2, f2, "b")]

    _compute_checksums(files)

    assert fd1.checksum == hashlib.sha1(b"hello").hexdigest()
    assert fd2.checksum == hashlib.sha1(b"world!!").hexdigest()


def test_expand_directories_http_keeps_imas_directory(tmp_path):
    # An IMAS (hdf5) directory must stay contained in its own folder.
    partition = tmp_path / "data"
    imas_dir = partition / "run" / "myids"
    imas_dir.mkdir(parents=True)
    (imas_dir / "master.h5").write_text("m")
    (imas_dir / "0001.h5").write_text("d")
    sim_uuid = uuid.uuid4()
    partitions = {"data": str(partition)}

    imas_file = FileData(
        type="IMAS",
        uri=SimDBUrl.build(
            scheme="imas", path="hdf5", host="", query=f"path={imas_dir}"
        ).encoded_string(),
        checksum="ignored",
        datetime=datetime.now(timezone.utc),
    )

    result = _expand_directories_http([imas_file], sim_uuid, partitions)

    targets = sorted(t for _, _, t in result)
    assert targets == [
        f"{sim_uuid.hex}/data/run/myids/0001.h5",
        f"{sim_uuid.hex}/data/run/myids/master.h5",
    ]
    assert all(file_data.type == "IMAS" for file_data, _, _ in result)


def test_expand_directories_http_unpartitioned_file_uses_file_scheme(tmp_path):
    # A file outside any partition falls back to the "file" namespace.
    f = tmp_path / "loose.txt"
    f.write_text("x")
    sim_uuid = uuid.uuid4()

    result = _expand_directories_http([_file_data(f)], sim_uuid, {})

    _, _, target = result[0]
    assert target == f"{sim_uuid.hex}/file/{str(f).lstrip('/')}"


def test_push_http_command_pushes_and_reports_success(tmp_path):
    runner = CliRunner()
    config_file = config_test_file()

    fake_api = mock.MagicMock()
    fake_api.get_validation_schemas.return_value = []
    fake_api.get_ingestion_status.return_value = "completed"

    sim = mock.MagicMock()
    sim.uuid = uuid.uuid4()
    fake_db = mock.MagicMock()
    fake_db.get_simulation.return_value = sim

    with mock.patch(
        "simdb.cli.commands.simulation.RemoteAPI", return_value=fake_api
    ), mock.patch("simdb.cli.commands.simulation.get_local_db", return_value=fake_db):
        result = runner.invoke(
            cli,
            [f"--config-file={config_file}", "simulation", "push_http", "iter", "sim1"],
        )

    assert result.exit_code == 0, result.output
    fake_api.push_http_simulation.assert_called_once_with(sim)
    assert "Successfully pushed simulation" in result.output


def test_push_http_command_fails_on_failed_status(tmp_path):
    runner = CliRunner()
    config_file = config_test_file()

    fake_api = mock.MagicMock()
    fake_api.get_validation_schemas.return_value = []
    fake_api.get_ingestion_status.return_value = "copy_failed"

    sim = mock.MagicMock()
    sim.uuid = uuid.uuid4()
    fake_db = mock.MagicMock()
    fake_db.get_simulation.return_value = sim

    with mock.patch(
        "simdb.cli.commands.simulation.RemoteAPI", return_value=fake_api
    ), mock.patch("simdb.cli.commands.simulation.get_local_db", return_value=fake_db):
        result = runner.invoke(
            cli,
            [f"--config-file={config_file}", "simulation", "push_http", "iter", "sim1"],
        )

    assert result.exit_code != 0
    assert "copy_failed" in result.output
