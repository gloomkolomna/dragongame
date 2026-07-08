"""add image_start/image_end to epic_stages, crosses_norm to epic_stage_actions

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-07-08 14:25:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'e3f4a5b6c7d8'
down_revision: Union[str, None] = 'd2e3f4a5b6c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('epic_stages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('image_start', sa.String(), nullable=True, server_default=''))
        batch_op.add_column(sa.Column('image_end', sa.String(), nullable=True, server_default=''))
    with op.batch_alter_table('epic_stage_actions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('crosses_norm', sa.Integer(), nullable=True, server_default='1000'))


def downgrade() -> None:
    with op.batch_alter_table('epic_stage_actions', schema=None) as batch_op:
        batch_op.drop_column('crosses_norm')
    with op.batch_alter_table('epic_stages', schema=None) as batch_op:
        batch_op.drop_column('image_end')
        batch_op.drop_column('image_start')
