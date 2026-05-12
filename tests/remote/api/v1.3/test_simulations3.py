import uuid

from conftest import (
    HEADERS,
    generate_simulation_data,
    generate_simulation_file,
)

from simdb.remote.models import (
    SimulationPostResponse3,
)


def post_simulation_v1_3(client, simulation_data, headers=HEADERS):
    rv_post = client.post(
        "/v1.3/simulations",
        json=simulation_data.model_dump(mode="json"),
        headers=headers,
        content_type="application/json",
    )
    return rv_post


def test_post_simulations_v1_3(client):
    """Test POST endpoint for creating a new simulation via v1.3 API."""
    simulation_data = generate_simulation_data(
        alias="test-simulation-v1.3",
        inputs=[generate_simulation_file()],
        outputs=[generate_simulation_file()],
    )

    rv = post_simulation_v1_3(client, simulation_data)

    assert rv.status_code == 200

    result = SimulationPostResponse3.model_validate(rv.json)
    assert result.job_id is not None


def test_post_simulations_v1_3_with_alias_auto_increment(client):
    """Test POST endpoint with alias ending in dash (auto-increment)."""
    random_name = uuid.uuid4().hex
    simulation_data = generate_simulation_data(
        alias=f"{random_name}-",
    )

    rv = post_simulation_v1_3(client, simulation_data)

    assert rv.status_code == 200
    result = SimulationPostResponse3.model_validate(rv.json)
    assert result.job_id is not None


def test_post_simulations_v1_3_no_alias(client):
    """Test POST endpoint with no alias provided (should use uuid.hex)."""
    simulation_data = generate_simulation_data()

    rv = post_simulation_v1_3(client, simulation_data)

    assert rv.status_code == 200
    result = SimulationPostResponse3.model_validate(rv.json)
    assert result.job_id is not None


def test_post_simulations_v1_3_with_inputs_outputs(client):
    """Test POST endpoint with inputs and outputs."""
    simulation_data = generate_simulation_data(
        alias="test-io-v1.3",
        inputs=[generate_simulation_file(), generate_simulation_file()],
        outputs=[generate_simulation_file()],
    )

    rv = post_simulation_v1_3(client, simulation_data)

    assert rv.status_code == 200
    result = SimulationPostResponse3.model_validate(rv.json)
    assert result.job_id is not None


def test_post_simulations_v1_3_uploaded_by(client):
    """Test POST endpoint with uploaded_by field."""
    simulation_data = generate_simulation_data(uploaded_by="test-user-v1.3")

    rv = post_simulation_v1_3(client, simulation_data)

    assert rv.status_code == 200
    result = SimulationPostResponse3.model_validate(rv.json)
    assert result.job_id is not None
