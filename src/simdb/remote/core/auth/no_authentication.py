
from flask import Request

from ....config import Config
from ._authenticator import Authenticator
from ._user import User


class NoopAuthenticator(Authenticator):
    """
    No-op authenticator which accepts any user as authenticated.
    """

    Name = "None"

    def authenticate(self, config: Config, request: Request) -> User | None:
        auth = request.authorization
        username = auth.username if auth is not None else None

        if username is None:
            return User("anonymous", None)

        return User(username, None)
