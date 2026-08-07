"""Tests for the HTTP push client helpers and CLI command."""

import hashlib
import uuid
from datetime import datetime, timezone
from unittest import mock

from click.testing import CliRunner
from utils import config_test_file

from simdb.cli.remote_api import _compute_checksums, _expand_directories_http
from simdb.cli.simdb import cli
from simdb.enums import IngestionStatus
from simdb.imas.utils import SimDBUrl
from simdb.remote.models import FileData


def _file_data(path) -> FileData:
    return FileData(
        type="FILE",
        uri=SimDBUrl.build(scheme="file", path=str(path), host="").encoded_string(),
        checksum="ignored",
        datetime=datetime.now(timezone.utc),
    )


def test_expand_directories_http_uses_absolute_paths(tmp_path):
    # HTTP uploads carry the file bytes, so partitions play no role: files keep
    # their absolute local path, namespaced under <uuid>/file/.
    (tmp_path / "subdir").mkdir()
    f = tmp_path / "subdir" / "file.txt"
    f.write_text("hello")
    sim_uuid = uuid.uuid4()

    result = _expand_directories_http([_file_data(f)], sim_uuid)

    assert len(result) == 1
    file_data, local_path, target = result[0]
    assert local_path == f
    assert target == f"{sim_uuid.hex}/file/{str(f).lstrip('/')}"
    parsed = SimDBUrl(file_data.uri)
    assert parsed.scheme == "http"
    assert parsed.host == sim_uuid.hex
    assert parsed.path == f"/file/{str(f).lstrip('/')}"
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
    imas_dir = tmp_path / "run" / "myids"
    imas_dir.mkdir(parents=True)
    (imas_dir / "master.h5").write_text("m")
    (imas_dir / "0001.h5").write_text("d")
    sim_uuid = uuid.uuid4()

    imas_file = FileData(
        type="IMAS",
        uri=SimDBUrl.build(
            scheme="imas", path="hdf5", host="", query=f"path={imas_dir}"
        ).encoded_string(),
        checksum="ignored",
        datetime=datetime.now(timezone.utc),
    )

    result = _expand_directories_http([imas_file], sim_uuid)

    prefix = f"{sim_uuid.hex}/file/{str(imas_dir).lstrip('/')}"
    targets = sorted(t for _, _, t in result)
    assert targets == [f"{prefix}/0001.h5", f"{prefix}/master.h5"]
    assert all(file_data.type == "IMAS" for file_data, _, _ in result)


def test_expand_directories_http_unpartitioned_file_uses_file_scheme(tmp_path):
    # No partition configuration is needed for HTTP uploads.
    f = tmp_path / "loose.txt"
    f.write_text("x")
    sim_uuid = uuid.uuid4()

    result = _expand_directories_http([_file_data(f)], sim_uuid)

    _, _, target = result[0]
    assert target == f"{sim_uuid.hex}/file/{str(f).lstrip('/')}"


def test_push_http_command_pushes_and_reports_success(tmp_path):
    runner = CliRunner()
    config_file = config_test_file()

    fake_api = mock.MagicMock()
    fake_api.get_validation_schemas.return_value = []
    fake_api.get_ingestion_status.return_value = IngestionStatus.COMPLETED

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
            catch_exceptions=False,
        )

    assert result.exit_code == 0, result.output
    fake_api.push_http_simulation.assert_called_once_with(sim, add_watcher=False)
    assert "Successfully pushed simulation" in result.output


def test_push_http_command_passes_add_watcher(tmp_path):
    runner = CliRunner()
    config_file = config_test_file()

    fake_api = mock.MagicMock()
    fake_api.get_validation_schemas.return_value = []
    fake_api.get_ingestion_status.return_value = IngestionStatus.COMPLETED

    sim = mock.MagicMock()
    sim.uuid = uuid.uuid4()
    fake_db = mock.MagicMock()
    fake_db.get_simulation.return_value = sim

    with mock.patch(
        "simdb.cli.commands.simulation.RemoteAPI", return_value=fake_api
    ), mock.patch("simdb.cli.commands.simulation.get_local_db", return_value=fake_db):
        result = runner.invoke(
            cli,
            [
                f"--config-file={config_file}",
                "simulation",
                "push_http",
                "iter",
                "sim1",
                "--add-watcher",
            ],
        )

    assert result.exit_code == 0, result.output
    fake_api.push_http_simulation.assert_called_once_with(sim, add_watcher=True)


def test_push_http_command_fails_on_failed_status(tmp_path):
    runner = CliRunner()
    config_file = config_test_file()

    fake_api = mock.MagicMock()
    fake_api.get_validation_schemas.return_value = []
    fake_api.get_ingestion_status.return_value = IngestionStatus.COPY_FAILED

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
    assert "COPY_FAILED" in result.output
