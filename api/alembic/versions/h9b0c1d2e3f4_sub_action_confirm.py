"""add confirm_button_label to epic_sub_actions

Revision ID: h9b0c1d2e3f4
Revises: g8a9b0c1d2e3
Create Date: 2026-07-12 08:20:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'h9b0c1d2e3f4'
down_revision: Union[str, None] = 'g8a9b0c1d2e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('epic_sub_actions') as batch:
        batch.add_column(sa.Column('confirm_button_label', sa.String(), nullable=True, server_default=''))


def downgrade() -> None:
    with op.batch_alter_table('epic_sub_actions') as batch:
        batch.drop_column('confirm_button_label')
