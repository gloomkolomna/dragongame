"""add description + confirm_button_label to epic_stage_actions

Revision ID: k2e3f4a5b6c7
Revises: j1d2e3f4a5b6
Create Date: 2026-07-12 10:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'k2e3f4a5b6c7'
down_revision: Union[str, None] = 'j1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('epic_stage_actions') as batch:
        batch.add_column(sa.Column('description', sa.Text(), nullable=True, server_default=''))
        batch.add_column(sa.Column('confirm_button_label', sa.String(), nullable=True, server_default=''))


def downgrade() -> None:
    with op.batch_alter_table('epic_stage_actions') as batch:
        batch.drop_column('confirm_button_label')
        batch.drop_column('description')
