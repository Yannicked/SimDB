import smtplib
from typing import List

from email_validator import validate_email

from simdb.config import SimDBSettings


class EmailServer:
    _server: str
    _port: int
    _user: str
    _password: str

    def __init__(self, config: SimDBSettings):
        self._server = config.email.server or ""
        self._port = config.email.port or 25
        self._user = config.email.user or ""
        self._password = config.email.password or ""

    def send_message(self, subject: str, body: str, to_addresses: List[str]):
        server = smtplib.SMTP(self._server, self._port)
        server.starttls()
        server.login(self._user, self._password)
        sent_to = [validate_email(i).email for i in to_addresses]
        sent_to_list = ",".join(sent_to)

        email_text = f"""\
From: {self._user}
To: {sent_to_list}
Subject: {subject}

{body}
"""

        server.sendmail(self._user, sent_to, email_text)
        server.close()
