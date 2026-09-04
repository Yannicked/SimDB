from enum import Enum


class IngestionStatus(str, Enum):
    QUEUED = "QUEUED"
    COPYING = "COPYING"
    COPIED = "COPIED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    COMPLETED = "COMPLETED"

    COPY_FAILED = "COPY_FAILED"
    VALIDATION_FAILED = "VALIDATION_FAILED"

    def is_terminal(self) -> bool:
        """Whether ingestion has finished and no worker task will touch the
        simulation again."""
        return self in (
            IngestionStatus.COMPLETED,
            IngestionStatus.COPY_FAILED,
            IngestionStatus.VALIDATION_FAILED,
        )
