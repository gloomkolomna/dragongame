"""drop action_type from epic_stage_actions (unused)

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-07-08 15:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'a5b6c7d8e9f0'
down_revision: Union[str, None] = 'f4a5b6c7d8e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c['name'] for c in sa.inspect(bind).get_columns('epic_stage_actions')}
    if 'action_type' in cols:
        with op.batch_alter_table('epic_stage_actions', schema=None) as batch_op:
            batch_op.drop_column('action_type')


def downgrade() -> None:
    with op.batch_alter_table('epic_stage_actions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('action_type', sa.String(), nullable=True, server_default=''))
