from pathlib import Path

import pytest
from pydantic import ValidationError

from simdb.cli.manifest import DataType, Manifest


def test_valid_manifest_loading_and_validation(tmp_path):
    # Setup some dummy input/output files to satisfy the file globbing check
    input_file = tmp_path / "input.json"
    input_file.write_text("{}")
    output_file = tmp_path / "output.json"
    output_file.write_text("{}")

    manifest_yaml = f"""\
manifest_version: 2
alias: test-simulation-alias
responsible_name: "John Doe"
inputs:
  - uri: file://{input_file.as_posix()}
  - uri: imas:///user?shot=10000&run=0&database=west
outputs:
  - uri: file://{output_file.as_posix()}
  - uri: imas:///user?shot=10000&run=1&database=west
metadata:
  - machine: ITER
  - code:
      name: METIS
  - description: sample description
"""
    manifest_file = tmp_path / "manifest.yaml"
    manifest_file.write_text(manifest_yaml)

    manifest = Manifest.load_from_file(manifest_file)

    assert manifest.manifest_version == 2
    assert manifest.version == 2
    assert manifest.alias == "test-simulation-alias"
    assert manifest.responsible_name == "John Doe"

    inputs = list(manifest.inputs)
    assert len(inputs) == 2
    assert inputs[0].type == DataType.FILE
    assert inputs[1].type == DataType.IMAS

    outputs = list(manifest.outputs)
    assert len(outputs) == 2
    assert outputs[0].type == DataType.FILE
    assert outputs[1].type == DataType.IMAS


def test_manifest_path_expansion_with_manifest_dir(tmp_path):
    # Setup some dummy file
    input_file = tmp_path / "test_input.json"
    input_file.write_text("{}")

    manifest_yaml = """\
manifest_version: 2
inputs:
  - uri: file:///$MANIFEST_DIR/test_input.json
outputs:
  - uri: imas:///user?shot=10000&run=1&database=west
"""
    manifest_file = tmp_path / "manifest.yaml"
    manifest_file.write_text(manifest_yaml)

    manifest = Manifest.load_from_file(manifest_file)

    inputs = list(manifest.inputs)
    assert len(inputs) == 1
    assert inputs[0].uri.path is not None
    assert Path(inputs[0].uri.path) == input_file


def test_invalid_manifest_version(tmp_path):
    # version must be 2
    manifest_yaml = """\
manifest_version: 1
inputs: []
outputs: []
"""
    manifest_file = tmp_path / "manifest.yaml"
    manifest_file.write_text(manifest_yaml)

    with pytest.raises(ValidationError, match="Input should be 2"):
        Manifest.load_from_file(manifest_file)


def test_manifest_version_must_be_integer(tmp_path):
    manifest_yaml = """\
manifest_version: "2"
inputs: []
outputs: []
"""
    manifest_file = tmp_path / "manifest.yaml"
    manifest_file.write_text(manifest_yaml)

    with pytest.raises(ValidationError, match="Input should be 2"):
        Manifest.load_from_file(manifest_file)


def test_missing_required_sections(tmp_path):
    # Missing required inputs/outputs sections
    manifest_yaml = """\
manifest_version: 2
alias: some-alias
"""
    manifest_file = tmp_path / "manifest.yaml"
    manifest_file.write_text(manifest_yaml)

    with pytest.raises(ValueError, match="Required manifest section"):
        Manifest.load_from_file(manifest_file)


def test_unknown_section(tmp_path):
    manifest_yaml = """\
manifest_version: 2
inputs: []
outputs: []
unknown_field: true
"""
    manifest_file = tmp_path / "manifest.yaml"
    manifest_file.write_text(manifest_yaml)

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Manifest.load_from_file(manifest_file)


def test_invalid_alias_characters(tmp_path):
    manifest_yaml = """\
manifest_version: 2
alias: "invalid alias"
inputs: []
outputs: []
"""
    manifest_file = tmp_path / "manifest.yaml"
    manifest_file.write_text(manifest_yaml)

    with pytest.raises(ValidationError, match="illegal characters in alias"):
        Manifest.load_from_file(manifest_file)


def test_duplicate_uris_in_inputs(tmp_path):
    manifest_yaml = """\
manifest_version: 2
inputs:
  - uri: imas:///user?shot=10000&run=0&database=west
  - uri: imas:///user?shot=10000&run=0&database=west
outputs: []
"""
    manifest_file = tmp_path / "manifest.yaml"
    manifest_file.write_text(manifest_yaml)

    with pytest.raises(ValidationError, match="Duplicate URI found in inputs"):
        Manifest.load_from_file(manifest_file)


def test_invalid_metadata_forbidden_characters(tmp_path):
    manifest_yaml = """\
manifest_version: 2
inputs: []
outputs: []
metadata:
  - "machine:name": "value"
"""
    manifest_file = tmp_path / "manifest.yaml"
    manifest_file.write_text(manifest_yaml)

    with pytest.raises(ValidationError, match="contains forbidden character"):
        Manifest.load_from_file(manifest_file)


def test_missing_files_causes_validation_error(tmp_path):
    manifest_yaml = """\
manifest_version: 2
inputs:
  - uri: file:///nonexistent_file_path_xyz.json
outputs: []
"""
    manifest_file = tmp_path / "manifest.yaml"
    manifest_file.write_text(manifest_yaml)

    with pytest.raises(ValidationError, match="No files found matching path"):
        Manifest.load_from_file(manifest_file)
