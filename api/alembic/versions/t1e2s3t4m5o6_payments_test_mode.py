"""payments test mode

Revision ID: t1e2s3t4m5o6
Revises: m1n2o3p4q5r6
Create Date: 2026-08-10 17:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 't1e2s3t4m5o6'
down_revision: Union[str, None] = 'm1n2o3p4q5r6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('app_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('payments_test_mode', sa.Boolean(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('payments_test_vk_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('app_settings', schema=None) as batch_op:
        batch_op.drop_column('payments_test_vk_id')
        batch_op.drop_column('payments_test_mode')
