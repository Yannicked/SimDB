"""convert_metadata_to_json_column

Revision ID: 28bee3aa2429
Revises: 9e9a4a7cd639
Create Date: 2026-02-26 17:01:30.925750

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

revision: str = '28bee3aa2429'
down_revision: Union[str, Sequence[str], None] = '9e9a4a7cd639'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    
    # Add metadata JSON column to simulations table
    # Use JSON type for PostgreSQL, Text for SQLite (will store JSON as text)
    if conn.dialect.name == 'postgresql':
        op.add_column('simulations', sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    else:
        op.add_column('simulations', sa.Column('metadata', sa.Text(), nullable=True))
    
    # Migrate existing metadata from metadata table to JSON column
    # First, we need to aggregate metadata by simulation
    if conn.dialect.name == 'postgresql':
        # PostgreSQL: Use json_object_agg
        migration_query = text("""
            UPDATE simulations 
            SET metadata = subq.meta_json
            FROM (
                SELECT sim_id, json_object_agg(element, value) as meta_json
                FROM metadata
                GROUP BY sim_id
            ) AS subq
            WHERE simulations.id = subq.sim_id
        """)
        conn.execute(migration_query)
    else:
        # SQLite: Build JSON manually using group_concat
        # This is more complex, we'll handle it per simulation
        result = conn.execute(text("SELECT DISTINCT sim_id FROM metadata"))
        sim_ids = [row[0] for row in result]
        
        for sim_id in sim_ids:
            # Get all metadata for this simulation
            meta_rows = conn.execute(
                text("SELECT element, value FROM metadata WHERE sim_id = :sim_id"),
                {"sim_id": sim_id}
            )
            
            # Build JSON object
            import json
            import pickle
            meta_dict = {}
            for element, value in meta_rows:
                # Value is stored as pickle, need to deserialize
                if value is not None:
                    try:
                        meta_dict[element] = pickle.loads(value) if isinstance(value, bytes) else value
                    except:
                        meta_dict[element] = value
                else:
                    meta_dict[element] = None
            
            conn.execute(
                text("UPDATE simulations SET metadata = :metadata WHERE id = :sim_id"),
                {"metadata": json.dumps(meta_dict), "sim_id": sim_id}
            )
    
    op.drop_index('metadata_index', table_name='metadata')
    op.drop_index(op.f('ix_metadata_sim_id'), table_name='metadata')
    op.drop_table('metadata')


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    
    # Recreate metadata table
    op.create_table(
        'metadata',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sim_id', sa.Integer(), nullable=True),
        sa.Column('element', sa.String(length=250), nullable=False),
        sa.Column('value', sa.PickleType(), nullable=True),
        sa.ForeignKeyConstraint(['sim_id'], ['simulations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_metadata_sim_id'), 'metadata', ['sim_id'], unique=False)
    op.create_index('metadata_index', 'metadata', ['sim_id', 'element'], unique=True)
    
    # Migrate data back from JSON column to metadata table
    if conn.dialect.name == 'postgresql':
        migration_query = text("""
            INSERT INTO metadata (sim_id, element, value)
            SELECT s.id, kv.key, kv.value::text
            FROM simulations s, json_each_text(s.metadata::json) kv
            WHERE s.metadata IS NOT NULL
        """)
        conn.execute(migration_query)
    else:
        # SQLite: Parse JSON and insert rows
        import json
        import pickle
        
        result = conn.execute(text("SELECT id, metadata FROM simulations WHERE metadata IS NOT NULL"))
        for sim_id, metadata_json in result:
            if metadata_json:
                try:
                    meta_dict = json.loads(metadata_json)
                    for element, value in meta_dict.items():
                        # Pickle the value for storage
                        pickled_value = pickle.dumps(value, 0)
                        conn.execute(
                            text("INSERT INTO metadata (sim_id, element, value) VALUES (:sim_id, :element, :value)"),
                            {"sim_id": sim_id, "element": element, "value": pickled_value}
                        )
                except:
                    pass
    
    op.drop_column('simulations', 'metadata')
