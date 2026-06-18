import importlib
import importlib.util
from typing import TYPE_CHECKING, ClassVar, cast
from unittest import mock

import pytest

from simdb.config import SimDBSettings, RoleSettings

has_easyad = importlib.util.find_spec("easyad") is not None
has_flask = importlib.util.find_spec("flask") is not None
if has_flask:
    from flask import Flask, Request

    from simdb.remote.core.auth import User, check_auth, check_role

if TYPE_CHECKING:
    from flask import Request


@pytest.mark.skipif(not has_flask, reason="requires flask library")
def test_check_role():
    app = Flask("test")
    config = SimDBSettings()
    config.roles["test_role"] = RoleSettings(users='user1,"user2", user3')
    app.simdb_config = config  # type: ignore
    with app.app_context():  # type: ignore
        ok = check_role(config, User("user1", ""), "test_role")
        assert ok
        ok = check_role(config, User("user4", ""), None)
        assert ok
        ok = check_role(config, User("user4", ""), "test_role")
        assert not ok


@mock.patch("simdb.remote.core.auth.active_directory.EasyAD")
@pytest.mark.skipif(not has_easyad, reason="requires easyad library")
@pytest.mark.skipif(not has_flask, reason="requires flask library")
def test_check_auth(easy_ad):
    config = SimDBSettings()
    config.server.admin_password = "abc123"
    config.authentication.type = "ActiveDirectory"
    config.authentication.ad_server = "test.server"
    config.authentication.ad_domain = "test.domain"
    config.authentication.ad_cert = "test.cert"

    class request:
        class authorization:
            username = ""
            password = ""

        headers: ClassVar[dict] = {}

    request.authorization.username = "admin"
    request.authorization.password = "abc123"
    ok = check_auth(config, cast(Request, request))
    assert ok

    def auth(user, password, **kwargs):
        if user == "user" and password == "password":
            return {"sAMAccountName": "user", "mail": "user@email.com"}
        return None

    easy_ad.return_value.authenticate_user.side_effect = auth
    request.authorization.username = "user"
    request.authorization.password = "password"
    ok = check_auth(config, cast(Request, request))
    assert ok
    easy_ad.assert_called_with(
        {
            "AD_SERVER": "test.server",
            "AD_DOMAIN": "test.domain",
            "AD_CA_CERT_FILE": "test.cert",
        }
    )
    easy_ad.return_value.authenticate_user.assert_called_once_with(
        "user", "password", json_safe=True
    )
    request.authorization.username = "user"
    request.authorization.password = "wrong"
    request.headers = {"Authorization": ""}
    ok = check_auth(config, cast(Request, request))
    assert not ok
