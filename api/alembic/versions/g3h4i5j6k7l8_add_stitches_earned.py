"""add stitches_earned to users

Revision ID: g3h4i5j6k7l8
Revises: a1b9c2d8e3f7
Create Date: 2026-07-14 07:20:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'g3h4i5j6k7l8'
down_revision: Union[str, None] = 'a1b9c2d8e3f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('stitches_earned', sa.Integer(), nullable=True))

    op.execute("UPDATE users SET stitches_earned = COALESCE(stitches_balance, 0)")


def downgrade() -> None:
    op.drop_column('users', 'stitches_earned')
