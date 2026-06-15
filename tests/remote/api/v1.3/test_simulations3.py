from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
from uuid import UUID

import pytest
from conftest import (
    HEADERS,
    generate_simulation_data,
)

from simdb.config import Config
from simdb.enums import IngestionStatus
from simdb.remote.models import (
    FileData,
    SimulationPostResponse,
)
from simdb.workers import tasks as simdb_tasks
from simdb.workers.celery import celery_app
from simdb.workers.tasks import _calculate_checksum


@pytest.fixture(autouse=True)
def celery_eager_config():

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    celery_app.conf.result_backend = None
    yield


@pytest.fixture
def client_with_task_mock(client, monkeypatch, tmp_path):
    db_file = tmp_path / "test.db"
    db_file.write_text("")
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()

    def mock_config():
        cfg = mock.MagicMock(spec=Config)
        cfg.get_option.side_effect = lambda key, **kwargs: {
            "database.type": "sqlite",
            "database.file": str(db_file),
            "server.upload_folder": str(upload_dir),
        }.get(key, kwargs.get("default"))
        cfg.get_string_option.side_effect = lambda key, **kwargs: {
            "database.type": "sqlite",
            "database.file": str(db_file),
            "server.upload_folder": str(upload_dir),
            "partition.data": str(tmp_path / "partition"),
        }.get(key, kwargs.get("default"))
        cfg.load = mock.MagicMock()
        return cfg

    monkeypatch.setattr(simdb_tasks, "Config", mock_config)
    monkeypatch.setattr(simdb_tasks, "get_db", lambda cfg: client.application.db)
    monkeypatch.setattr(client.application.db, "close", lambda: None)

    return client


def post_simulation_v13(client, simulation_data, headers=HEADERS):
    rv_post = client.post(
        "/v1.3/simulations",
        json=simulation_data.model_dump(mode="json"),
        headers=headers,
        content_type="application/json",
    )
    return rv_post


def get_simulation_status(client, simulation_uuid: UUID, headers=HEADERS):
    rv_get = client.get(
        f"/v1.3/simulation/status/{simulation_uuid.hex}", headers=headers
    )
    return rv_get


def generate_simulation_file(path) -> FileData:
    file_path = path / "partition/file.txt"
    file_path.parent.mkdir(exist_ok=True)
    file_path.write_text("test data")
    checksum = _calculate_checksum(file_path)
    return FileData(
        type="FILE",
        uri="data:///file.txt",
        checksum=checksum,
        datetime=datetime.now(timezone.utc),
    )


def test_post_simulations_v13(client_with_task_mock, tmp_path):
    """Test POST endpoint for creating a new simulation."""
    client = client_with_task_mock
    simulation_data = generate_simulation_data(
        alias="test-simulation-v13",
        inputs=[generate_simulation_file(tmp_path)],
        outputs=[generate_simulation_file(tmp_path)],
    )

    rv = post_simulation_v13(client, simulation_data)

    assert rv.status_code == 200

    result = SimulationPostResponse.model_validate(rv.json)
    assert result.ingested == simulation_data.simulation.uuid

    simulation = client.application.db.get_simulation(result.ingested.hex)
    assert simulation.ingestion_status == IngestionStatus.COMPLETED
    assert (
        Path(simulation.inputs[0].uri.path)
        == tmp_path / "uploads" / result.ingested.hex / "file.txt"
    )
