"""families_and_per_family_grid

Revision ID: 359d89020f12
Revises: a67adbf490cd
Create Date: 2026-07-02 12:22:59.942728
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '359d89020f12'
down_revision: Union[str, None] = 'a67adbf490cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('families',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Insert default family so existing data has something to reference
    op.execute("INSERT INTO families (name, description, sort_order) VALUES ('Основное', '', 0)")

    with op.batch_alter_table('dragons', schema=None) as batch_op:
        batch_op.add_column(sa.Column('family_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_dragons_family', 'families', ['family_id'], ['id'], ondelete='SET NULL')

    with op.batch_alter_table('collection_grid', schema=None) as batch_op:
        batch_op.add_column(sa.Column('family_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_grid_family', 'families', ['family_id'], ['id'], ondelete='CASCADE')

    # Assign default family to existing rows, then make NOT NULL
    op.execute("UPDATE collection_grid SET family_id = 1 WHERE family_id IS NULL")

    with op.batch_alter_table('collection_grid', schema=None, recreate='always') as batch_op:
        batch_op.alter_column('family_id', nullable=False)
        batch_op.create_unique_constraint('uq_grid_cell', ['family_id', 'cell_x', 'cell_y'])


def downgrade() -> None:
    with op.batch_alter_table('collection_grid', schema=None, recreate='always') as batch_op:
        batch_op.drop_constraint('uq_grid_cell', type_='unique')
        batch_op.drop_constraint('fk_grid_family', type_='foreignkey')
        batch_op.drop_column('family_id')

    with op.batch_alter_table('dragons', schema=None) as batch_op:
        batch_op.drop_constraint('fk_dragons_family', type_='foreignkey')
        batch_op.drop_column('family_id')

    op.drop_table('families')
