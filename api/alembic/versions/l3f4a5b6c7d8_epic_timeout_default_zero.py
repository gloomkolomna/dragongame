"""default epic timeout to 0 (no timer)

Revision ID: l3f4a5b6c7d8
Revises: k2e3f4a5b6c7
Create Date: 2026-07-12 10:45:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'l3f4a5b6c7d8'
down_revision: Union[str, None] = 'k2e3f4a5b6c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('epic_stage_actions') as batch:
        batch.alter_column('timeout_hours', server_default='0')
    with op.batch_alter_table('epic_sub_action_steps') as batch:
        batch.alter_column('timeout_hours', server_default='0')


def downgrade() -> None:
    with op.batch_alter_table('epic_stage_actions') as batch:
        batch.alter_column('timeout_hours', server_default='24')
    with op.batch_alter_table('epic_sub_action_steps') as batch:
        batch.alter_column('timeout_hours', server_default='24')
