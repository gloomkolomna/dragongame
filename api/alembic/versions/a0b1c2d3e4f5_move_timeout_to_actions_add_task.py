"""move timeout from stages to actions, add task field

Revision ID: a0b1c2d3e4f5
Revises: f4a5b6c7d8e9
Create Date: 2026-07-09 08:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'a0b1c2d3e4f5'
down_revision: Union[str, None] = 'f4a5b6c7d8e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('epic_stages', schema=None) as batch_op:
        batch_op.drop_column('care_timeout_hours')
        batch_op.drop_column('care_timeout_minutes')

    with op.batch_alter_table('epic_stage_actions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('task', sa.Text(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('timeout_hours', sa.Integer(), nullable=False, server_default='24'))
        batch_op.add_column(sa.Column('timeout_minutes', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    with op.batch_alter_table('epic_stages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('care_timeout_hours', sa.Integer(), nullable=False, server_default='24'))
        batch_op.add_column(sa.Column('care_timeout_minutes', sa.Integer(), nullable=False, server_default='0'))

    with op.batch_alter_table('epic_stage_actions', schema=None) as batch_op:
        batch_op.drop_column('timeout_minutes')
        batch_op.drop_column('timeout_hours')
        batch_op.drop_column('task')
