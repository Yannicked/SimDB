from enum import Enum


class IngestionStatus(str, Enum):
    QUEUED = "queued"
    COPYING = "copying"
    COPIED = "copied"
    VALIDATING = "validating"
    VALIDATED = "validated"
    COMPLETED = "completed"
