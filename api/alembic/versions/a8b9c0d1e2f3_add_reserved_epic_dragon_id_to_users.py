"""add reserved_epic_dragon_id to users

Revision ID: a8b9c0d1e2f3
Revises: 7f3a1c9e2b48
Create Date: 2026-07-24 13:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'a8b9c0d1e2f3'
down_revision: Union[str, None] = '7f3a1c9e2b48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('reserved_epic_dragon_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'reserved_epic_dragon_id')
