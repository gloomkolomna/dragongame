"""add epic_cost_stitches to dragons

Revision ID: p7q8r9s0t1
Revises: o6p7q8r9s0t1
Create Date: 2026-07-13 11:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'p7q8r9s0t1'
down_revision: Union[str, None] = 'o6p7q8r9s0t1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE dragons ADD COLUMN epic_cost_stitches INTEGER")


def downgrade() -> None:
    op.execute("ALTER TABLE dragons DROP COLUMN epic_cost_stitches")
