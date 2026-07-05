"""merge rarity 4 into 3

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-05 12:40:00.000000
"""
from typing import Sequence, Union
from alembic import op


revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE dragons SET rarity = 3 WHERE rarity = 4")


def downgrade() -> None:
    # cannot revert data migration
    pass
