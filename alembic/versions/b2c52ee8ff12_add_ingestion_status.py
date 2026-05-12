"""Add ingestion status

Revision ID: b2c52ee8ff12
Revises: 9e9a4a7cd639
Create Date: 2026-05-11 16:16:03.768893

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c52ee8ff12"
down_revision: Union[str, Sequence[str], None] = "9e9a4a7cd639"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("simulations", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "ingestion_status",
                sa.Enum(
                    "QUEUED",
                    "COPYING",
                    "VALIDATING",
                    "COMPLETED",
                    name="ingestionstatus",
                ),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column("ingestion_version", sa.Integer(), nullable=False)
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("simulations", schema=None) as batch_op:
        batch_op.drop_column("ingestion_version")
        batch_op.drop_column("ingestion_status")
