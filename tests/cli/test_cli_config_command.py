from click.testing import CliRunner
from utils import config_test_file

from simdb.cli.simdb import cli
from simdb.config import SimDBSettings


def test_config_get():
    config_file = config_test_file()
    runner = CliRunner()
    result = runner.invoke(
        cli, [f"--config-file={config_file}", "config", "get", "remote.test.url"]
    )
    assert result.exception is None
    assert "http://0.0.0.0:5000/" in result.output


def test_config_set():
    config_file = config_test_file()
    runner = CliRunner()
    result = runner.invoke(
        cli, [f"--config-file={config_file}", "config", "set", "remote.test.url", "http://new.url/"]
    )
    assert result.exception is None
    config = SimDBSettings.load(config_file)
    assert config.remotes["test"].url == "http://new.url/"
