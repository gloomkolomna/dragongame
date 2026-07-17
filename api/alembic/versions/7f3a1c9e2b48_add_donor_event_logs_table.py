"""add donor event logs table

Revision ID: 7f3a1c9e2b48
Revises: 24562e9a6d15
Create Date: 2026-07-17 08:55:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '7f3a1c9e2b48'
down_revision: Union[str, None] = '24562e9a6d15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('donor_event_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('vk_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=True),
        sa.Column('synced_at', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_id')
    )


def downgrade() -> None:
    op.drop_table('donor_event_logs')
