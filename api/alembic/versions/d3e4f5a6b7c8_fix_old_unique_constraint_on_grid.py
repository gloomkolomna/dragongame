"""fix old unique constraint on collection_grid

Revision ID: d3e4f5a6b7c8
Revises: bf1b946df94e
Create Date: 2026-07-04 20:10:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, None] = 'bf1b946df94e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()

    indexes = connection.execute(sa.text("PRAGMA index_list('collection_grid')")).fetchall()
    for idx in indexes:
        if idx[2] == 1:
            cols = connection.execute(sa.text(f"PRAGMA index_info('{idx[1]}')")).fetchall()
            col_names = [c[2] for c in cols]
            if sorted(col_names) == ['cell_x', 'cell_y']:
                op.execute(sa.text(f"DROP INDEX {idx[1]}"))
                break


def downgrade() -> None:
    with op.batch_alter_table('collection_grid', schema=None) as batch_op:
        batch_op.create_unique_constraint(None, ['cell_x', 'cell_y'])
