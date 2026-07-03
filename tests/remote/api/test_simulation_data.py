"""Tests for the /simulation/<sim_id>/data endpoint helpers."""

import imas
import pytest
from imas.ids_defs import IDS_TIME_MODE_HOMOGENEOUS

from simdb.remote.apis.v1_2 import simulation_data


@pytest.fixture
def summary_entry(tmp_path):
    """Write a minimal summary IDS to HDF5, return a read-mode DBEntry."""
    uri = f"imas:hdf5?path={tmp_path}"
    with imas.DBEntry(uri, "x") as entry:
        summary = entry.factory.new("summary")
        summary.ids_properties.homogeneous_time = IDS_TIME_MODE_HOMOGENEOUS
        summary.global_quantities.ip.value = [1.5e6]
        summary.time = [0.0]
        entry.put(summary)
    return imas.DBEntry(uri, "r")


def test_get_ids_node_returns_correct_value(summary_entry):
    """Happy path: _get_ids_node returns the real IDSPrimitive with correct value."""
    with summary_entry as entry:
        node = simulation_data._get_ids_node(
            entry, "summary", 0, "global_quantities/ip/value"
        )

    assert node.has_value
    assert list(node.value) == [1.5e6]
    assert node.metadata.units == "A"


def test_get_ids_node_with_dd_version_returns_converted_value(summary_entry):
    """convert_ids round-trip with matching dd_version preserves value."""
    with summary_entry as entry:
        stored_version = entry.factory.version
        node = simulation_data._get_ids_node(
            entry,
            "summary",
            0,
            "global_quantities/ip/value",
            dd_version=stored_version,
        )

    assert node.has_value
    assert list(node.value) == [1.5e6]
