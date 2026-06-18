from typing import Optional

from flask import Request

from simdb.config import SimDBSettings

from ._authenticator import Authenticator
from ._exceptions import AuthenticationError
from ._user import User


class FirewallAuthenticator(Authenticator):
    Name = "Firewall"

    def authenticate(self, config: SimDBSettings, request: Request) -> Optional[User]:
        firewall_user = config.authentication.firewall_user
        firewall_email = config.authentication.firewall_email

        if not firewall_user:
            raise AuthenticationError(
                "Firewall auth enabled but authentication.firewall_user not defined"
            )

        if not firewall_email:
            raise AuthenticationError(
                "Firewall auth enabled but authentication.firewall_email not defined"
            )

        if firewall_user not in request.headers:
            raise AuthenticationError(f"Header {firewall_user} not found")

        if firewall_email not in request.headers:
            raise AuthenticationError(f"Header {firewall_email} not found")

        return User(request.headers[firewall_user], request.headers[firewall_email])
