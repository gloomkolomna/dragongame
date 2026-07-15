"""add dragon_reservations table

Revision ID: m5n6o7p8q9r0
Revises: l4m5n6o7p8q9
Create Date: 2026-07-15 20:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'm5n6o7p8q9r0'
down_revision: Union[str, None] = 'l4m5n6o7p8q9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'dragon_reservations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('vk_url', sa.String(), nullable=False),
        sa.Column('vk_user_id', sa.Integer(), nullable=True),
        sa.Column('dragon_id', sa.Integer(), sa.ForeignKey('dragons.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(20), nullable=True, server_default='reserved'),
        sa.Column('notes', sa.Text(), nullable=True, server_default=''),
        sa.Column('created_at', sa.String(), nullable=True, server_default=''),
        sa.Column('updated_at', sa.String(), nullable=True, server_default=''),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('dragon_reservations')
