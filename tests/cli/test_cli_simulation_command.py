from unittest import mock

from click.testing import CliRunner
from utils import config_test_file

from simdb.cli.simdb import cli


@mock.patch("simdb.database.get_local_db")
@mock.patch("simdb.cli.remote_api.RemoteAPI")
def test_simulation_alias_command(remote_api, get_local_db):
    config_file = config_test_file()
    runner = CliRunner()
    result = runner.invoke(cli, [f"--config-file={config_file}", "simulation"])
    assert result.exception is None


@mock.patch("simdb.database.get_local_db")
@mock.patch("simdb.cli.remote_api.RemoteAPI")
def test_simulation_delete_command(remote_api, get_local_db):
    config_file = config_test_file()
    runner = CliRunner()
    result = runner.invoke(cli, [f"--config-file={config_file}", "simulation"])
    assert result.exception is None


@mock.patch("simdb.database.get_local_db")
@mock.patch("simdb.cli.remote_api.RemoteAPI")
def test_simulation_info_command(remote_api, get_local_db):
    config_file = config_test_file()
    runner = CliRunner()
    result = runner.invoke(cli, [f"--config-file={config_file}", "simulation"])
    assert result.exception is None


@mock.patch("simdb.database.get_local_db")
@mock.patch("simdb.cli.remote_api.RemoteAPI")
def test_simulation_list_command(remote_api, get_local_db):
    config_file = config_test_file()
    runner = CliRunner()
    result = runner.invoke(cli, [f"--config-file={config_file}", "simulation"])
    assert result.exception is None


@mock.patch("simdb.database.get_local_db")
@mock.patch("simdb.cli.remote_api.RemoteAPI")
def test_simulation_modify_command(remote_api, get_local_db):
    config_file = config_test_file()
    runner = CliRunner()
    result = runner.invoke(cli, [f"--config-file={config_file}", "simulation"])
    assert result.exception is None


@mock.patch("simdb.database.get_local_db")
@mock.patch("simdb.cli.remote_api.RemoteAPI")
def test_simulation_new_command(remote_api, get_local_db):
    config_file = config_test_file()
    runner = CliRunner()
    result = runner.invoke(cli, [f"--config-file={config_file}", "simulation"])
    assert result.exception is None


@mock.patch("simdb.database.get_local_db")
@mock.patch("simdb.cli.remote_api.RemoteAPI")
def test_simulation_push_command(remote_api, get_local_db):
    config_file = config_test_file()
    runner = CliRunner()
    result = runner.invoke(cli, [f"--config-file={config_file}", "simulation"])
    assert result.exception is None


@mock.patch("simdb.database.get_local_db")
@mock.patch("simdb.cli.remote_api.RemoteAPI")
def test_simulation_query_command(remote_api, get_local_db):
    config_file = config_test_file()
    runner = CliRunner()
    result = runner.invoke(cli, [f"--config-file={config_file}", "simulation"])
    assert result.exception is None


@mock.patch("simdb.database.get_local_db")
@mock.patch("simdb.cli.remote_api.RemoteAPI")
def test_simulation_validate_command(remote_api, get_local_db):
    config_file = config_test_file()
    runner = CliRunner()
    result = runner.invoke(cli, [f"--config-file={config_file}", "simulation"])
    assert result.exception is None


@mock.patch("simdb.cli.commands.simulation.show_quantity_textual_plot")
@mock.patch("simdb.cli.commands.simulation.RemoteAPI")
def test_simulation_data_command(mock_remote_api_cls, mock_textual_plot):
    """``simdb simulation data`` prints field info."""
    mock_api = mock_remote_api_cls.return_value
    mock_api.get_simulation_data.return_value = {
        "simulation": "a304a6955b3f11f1809bd4f5ef75ec04",
        "path": "core_profiles/profiles_1d[0]/electrons/temperature",
        "occurrence": 0,
        "field": {
            "name": "core_profiles/profiles_1d[0]/electrons/temperature",
            "units": "eV",
            "data": [1000.0, 1200.0, 900.0],
        },
        "coordinates": [
            {
                "name": "core_profiles/profiles_1d[0]/grid/rho_tor_norm",
                "units": "",
                "data": [0.0, 0.5, 1.0],
            }
        ],
    }

    config_file = config_test_file()
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            f"--config-file={config_file}",
            "simulation",
            "data",
            "test_sim",
            "core_profiles/profiles_1d[0]/electrons/temperature",
        ],
    )

    assert result.exception is None, result.output
    mock_api.get_simulation_data.assert_called_once_with(
        "test_sim", "core_profiles/profiles_1d[0]/electrons/temperature"
    )
    result_data = mock_api.get_simulation_data.return_value
    mock_textual_plot.assert_called_once_with(
        result_data["field"],
        label="field",
        x_quantity=result_data["coordinates"][0],
    )
    assert "simulation : a304a6955b3f11f1809bd4f5ef75ec04" in result.output
    assert "shape (3,)" not in result.output
    assert "1000" not in result.output
    assert "1200" not in result.output
