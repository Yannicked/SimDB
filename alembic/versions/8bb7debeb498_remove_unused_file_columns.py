"""Remove unused file columns

Revision ID: 8bb7debeb498
Revises: 9e9a4a7cd639
Create Date: 2026-05-12 15:05:57.886659

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8bb7debeb498"
down_revision: Union[str, Sequence[str], None] = "9e9a4a7cd639"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("files", schema=None) as batch_op:
        batch_op.drop_column("usage")
        batch_op.drop_column("access")
        batch_op.drop_column("purpose")
        batch_op.drop_column("sensitivity")
        batch_op.drop_column("embargo")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("files", schema=None) as batch_op:
        batch_op.add_column(sa.Column("embargo", sa.VARCHAR(length=20), nullable=True))
        batch_op.add_column(
            sa.Column("sensitivity", sa.VARCHAR(length=20), nullable=True)
        )
        batch_op.add_column(sa.Column("purpose", sa.VARCHAR(length=250), nullable=True))
        batch_op.add_column(sa.Column("access", sa.VARCHAR(length=20), nullable=True))
        batch_op.add_column(sa.Column("usage", sa.VARCHAR(length=250), nullable=True))
