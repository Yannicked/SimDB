from sqlalchemy import Column
from sqlalchemy import types as sql_types
from sqlalchemy.orm import validates

from simdb.docstrings import inherit_docstrings
from simdb.notifications import Notification

from .base import Base
from .types import ChoiceType
from .utils import checked_get

try:
    from email_validator import validate_email
except ImportError:
    validate_email = None

NOTIFICATION_CHOICES = {
    Notification.VALIDATION: "V",
    Notification.REVISION: "R",
    Notification.OBSOLESCENCE: "O",
    Notification.ALL: "A",
}


@inherit_docstrings
class Watcher(Base):
    """Class to represent people watching simulations for updates."""

    __tablename__ = "watchers"
    id = Column(sql_types.Integer, primary_key=True)
    username = Column(sql_types.String(250))
    email = Column(sql_types.String(1000))
    notification = Column(
        ChoiceType(choices=NOTIFICATION_CHOICES, length=1, enum_type=Notification)
    )

    @validates("email")
    def validate_email_address(self, key, address):
        if validate_email is not None:
            validate_email(address)
        return address

    def __init__(self, username: str, email: str, notification: "Watcher.Notification"):
        self.username = username
        self.email = email
        self.notification = notification

    @classmethod
    def from_data(cls, data: dict) -> "Watcher":
        username = checked_get(data, "username", str)
        email = checked_get(data, "email", str)
        notification = checked_get(data, "notification", str)
        watcher = Watcher(username, email, notification)
        return watcher

    def data(self, recurse: bool = False) -> dict[str, str]:
        data = {
            "username": self.username,
            "email": self.email,
            "notification": str(self.notification),
        }
        return data
