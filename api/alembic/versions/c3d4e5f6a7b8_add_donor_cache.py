"""add donor_cache

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-09 15:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('donor_cache',
        sa.Column('vk_id', sa.Integer(), nullable=False),
        sa.Column('is_don', sa.Boolean(), nullable=True),
        sa.Column('don_since', sa.String(), nullable=True),
        sa.Column('updated_at', sa.String(), nullable=True),
        sa.Column('last_synced_at', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('vk_id')
    )


def downgrade() -> None:
    op.drop_table('donor_cache')
