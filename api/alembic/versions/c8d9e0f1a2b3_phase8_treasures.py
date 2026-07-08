"""phase 8: treasures + user_treasures

Revision ID: c8d9e0f1a2b3
Revises: b1c2d3e4f5a6
Create Date: 2026-07-08 21:40:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'c8d9e0f1a2b3'
down_revision: Union[str, None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if 'treasures' not in insp.get_table_names():
        op.create_table(
            'treasures',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('description', sa.Text(), server_default=''),
            sa.Column('image_path', sa.String(), server_default=''),
            sa.Column('dragon_id', sa.Integer(), nullable=False),
            sa.Column('is_active', sa.Boolean(), server_default='1'),
            sa.ForeignKeyConstraint(['dragon_id'], ['dragons.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('dragon_id'),
        )

    if 'user_treasures' not in insp.get_table_names():
        op.create_table(
            'user_treasures',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('treasure_id', sa.Integer(), nullable=False),
            sa.Column('acquired_at', sa.String(), server_default=''),
            sa.ForeignKeyConstraint(['user_id'], ['users.vk_id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['treasure_id'], ['treasures.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('user_id', 'treasure_id'),
        )


def downgrade() -> None:
    op.drop_table('user_treasures')
    op.drop_table('treasures')
