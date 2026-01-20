from unittest import mock

from click.testing import CliRunner
from utils import config_test_file

from simdb.cli.simdb import cli


@mock.patch("simdb.database.Database.reset")
def test_database_clear_command(reset):
    config_file = config_test_file()
    runner = CliRunner()
    result = runner.invoke(cli, [f"--config-file={config_file}", "database", "clear"])
    assert result.exception is None
    assert reset.called
