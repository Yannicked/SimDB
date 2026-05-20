from enum import Enum


class IngestionStatus(str, Enum):
    QUEUED = "queued"
    COPYING = "copying"
    COPIED = "copied"
    VALIDATING = "validating"
    VALIDATED = "validated"
    COMPLETED = "completed"

    COPY_FAILED = "copy_failed"
    VALIDATION_FAILED = "validation_failed"
