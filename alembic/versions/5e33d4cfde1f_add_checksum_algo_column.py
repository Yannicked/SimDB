"""Add checksum algo column

Revision ID: 5e33d4cfde1f
Revises: 28bee3aa2429
Create Date: 2026-07-01 15:23:58.624184

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5e33d4cfde1f"
down_revision: Union[str, Sequence[str], None] = "28bee3aa2429"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == "postgresql":
        op.execute("CREATE TYPE checksumalgo AS ENUM ('sha1', 'sha256', 'unknown')")
    with op.batch_alter_table("files", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "checksum_algo",
                sa.Enum("sha1", "sha256", "unknown", name="checksumalgo"),
                nullable=True,
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("files", schema=None) as batch_op:
        batch_op.drop_column("checksum_algo")
