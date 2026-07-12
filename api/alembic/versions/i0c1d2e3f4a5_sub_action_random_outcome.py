"""add random_outcome to epic_sub_actions

Revision ID: i0c1d2e3f4a5
Revises: h9b0c1d2e3f4
Create Date: 2026-07-12 09:20:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'i0c1d2e3f4a5'
down_revision: Union[str, None] = 'h9b0c1d2e3f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('epic_sub_actions') as batch:
        batch.add_column(sa.Column('random_outcome', sa.Boolean(), nullable=True, server_default=sa.text('1')))


def downgrade() -> None:
    with op.batch_alter_table('epic_sub_actions') as batch:
        batch.drop_column('random_outcome')
