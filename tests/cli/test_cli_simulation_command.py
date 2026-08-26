from unittest import mock

import pytest
from click.testing import CliRunner
from utils import config_test_file

from simdb.cli.simdb import cli
from simdb.enums import IngestionStatus


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


@pytest.mark.parametrize(
    "subcommand, trailing_args",
    (
        ("push", ()),
        ("push_local", ()),
        ("pull", ("directory",)),
        ("data", ("ids_path",)),
    ),
)
@pytest.mark.parametrize(
    "options", (("--username", "bob"), ()), ids=("username", "none")
)
@pytest.mark.parametrize(
    "options_first", (True, False), ids=("options-first", "options-last")
)
@pytest.mark.parametrize("remote", (("test",), ()), ids=("test", "default"))
@mock.patch("simdb.cli.commands.simulation.RemoteAPI")
@mock.patch("simdb.cli.commands.simulation.get_local_db")
def test_optional_remote_argument(
    get_local_db, remote_api, remote, options_first, options, subcommand, trailing_args
):
    """REMOTE may be left out, wherever the options appear on the command line."""
    config_file = config_test_file()
    # push_local polls until the ingestion reaches a terminal state.
    remote_api.return_value.get_ingestion_status.return_value = (
        IngestionStatus.COMPLETED.value
    )
    arguments = (*remote, "sim_id", *trailing_args)
    argv = (*options, *arguments) if options_first else (*arguments, *options)

    runner = CliRunner()
    result = runner.invoke(
        cli, [f"--config-file={config_file}", "simulation", subcommand, *argv]
    )

    assert remote_api.called, result.output
    used_remote, used_username = remote_api.call_args.args[:2]
    assert used_remote == (remote[0] if remote else "")
    assert used_username == ("bob" if options else None)
