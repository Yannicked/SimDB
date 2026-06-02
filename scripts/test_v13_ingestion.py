#!/usr/bin/env python3
"""Test script for v1.3 simulation ingestion against a running server."""

import base64
import sys
import time
import uuid
from datetime import datetime, timezone

import requests
from pydantic import TypeAdapter

try:
    from simdb.remote.models import (
        FileData,
        FileDataList,
        MetadataData,
        MetadataDataList,
        SimulationData,
        SimulationPostData,
        SimulationPostResponse,
        SimulationStatusResponse,
    )
except ImportError:
    print("ERROR: simdb package not installed. Run: pip install -e .")
    sys.exit(1)

SERVER_URL = "http://localhost:5000"
API_VERSION = "v1.3"
TEST_PASSWORD = "CHANGE_ME"

CREDENTIALS = base64.b64encode(f"admin:{TEST_PASSWORD}".encode()).decode()
HEADERS = {"Authorization": f"Basic {CREDENTIALS}"}


def generate_simulation_file():
    return FileData(
        type="FILE",
        uri="data:///subdir/test_file.txt",
        checksum="fake_checksum",
        datetime=datetime.now(timezone.utc),
    )


def generate_simulation_data(
    alias=None,
    inputs=None,
    outputs=None,
    metadata=None,
    add_watcher=False,
    uploaded_by=None,
):
    if alias is None:
        alias = f"test-{uuid.uuid4().hex[:8]}"
    if inputs is None:
        inputs = [generate_simulation_file()]
    if outputs is None:
        outputs = [generate_simulation_file()]

    simulation = SimulationData(
        alias=alias,
        inputs=FileDataList(root=inputs),
        outputs=FileDataList(root=outputs),
    )

    if metadata:
        simulation.metadata = MetadataDataList(root=metadata)

    data = SimulationPostData(
        simulation=simulation,
        add_watcher=add_watcher,
        uploaded_by=uploaded_by,
    )
    return data


def post_simulation(simulation_data, retries=5, delay=2):
    url = f"{SERVER_URL}/{API_VERSION}/simulations"
    for attempt in range(retries):
        try:
            response = requests.post(
                url,
                json=simulation_data.model_dump(mode="json"),
                headers={**HEADERS, "Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                raise


def get_simulation_status(sim_id):
    url = f"{SERVER_URL}/{API_VERSION}/simulation/status/{sim_id}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response


def wait_for_completion(sim_id, timeout=60, interval=2):
    start = time.time()
    while time.time() - start < timeout:
        response = get_simulation_status(sim_id)
        status_data = SimulationStatusResponse.model_validate(response.json())
        print(f"  Status: {status_data.status}")
        if status_data.status.name in ("COMPLETED", "FAILED"):
            return status_data
        time.sleep(interval)
    raise TimeoutError(f"Simulation {sim_id} did not complete within {timeout}s")


def main():
    print("=" * 60)
    print("v1.3 Simulation Ingestion Test")
    print("=" * 60)
    print(f"Server: {SERVER_URL}")
    print(f"API Version: {API_VERSION}")
    print()

    print("Generating simulation data...")
    simulation_data = generate_simulation_data(
        alias=f"test-ingestion-{uuid.uuid4().hex}",
        inputs=[generate_simulation_file()],
        outputs=[generate_simulation_file()],
        uploaded_by="test-script",
    )
    print(f"  Alias: {simulation_data.simulation.alias}")
    print(f"  UUID: {simulation_data.simulation.uuid}")
    print()

    print("Posting simulation for ingestion...")
    try:
        response = post_simulation(simulation_data, retries=1)
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to post simulation: {e}")
        sys.exit(1)

    result = SimulationPostResponse.model_validate(response.json())
    print(f"  Ingested UUID: {result.ingested}")
    if result.error:
        print(f"  Error: {result.error}")
    print()

    print("Waiting for ingestion to complete...")
    try:
        final_status = wait_for_completion(result.ingested)
        print()
        print("=" * 60)
        print(f"SUCCESS: Ingestion completed with status {final_status.status}")
        print("=" * 60)
    except TimeoutError as e:
        print()
        print("=" * 60)
        print(f"WARNING: {e}")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
