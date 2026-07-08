"""phase 3: legend progress table + shop_items.is_legend_book

Revision ID: b1c2d3e4f5a6
Revises: a5b6c7d8e9f0
Create Date: 2026-07-08 16:55:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'a5b6c7d8e9f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    cols = {c['name'] for c in insp.get_columns('shop_items')}
    if 'is_legend_book' not in cols:
        with op.batch_alter_table('shop_items', schema=None) as batch_op:
            batch_op.add_column(sa.Column('is_legend_book', sa.Boolean(), nullable=True, server_default='0'))

    if 'user_legend_progress' not in insp.get_table_names():
        op.create_table(
            'user_legend_progress',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('dragon_id', sa.Integer(), nullable=False),
            sa.Column('fragment_number', sa.Integer(), nullable=False),
            sa.Column('photo_before_id', sa.Text(), server_default=''),
            sa.Column('photo_after_id', sa.Text(), server_default=''),
            sa.Column('completed', sa.Boolean(), server_default='0'),
            sa.Column('completed_at', sa.String(), server_default=''),
            sa.ForeignKeyConstraint(['user_id'], ['users.vk_id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['dragon_id'], ['dragons.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('user_id', 'dragon_id', 'fragment_number'),
        )


def downgrade() -> None:
    op.drop_table('user_legend_progress')
    with op.batch_alter_table('shop_items', schema=None) as batch_op:
        batch_op.drop_column('is_legend_book')
