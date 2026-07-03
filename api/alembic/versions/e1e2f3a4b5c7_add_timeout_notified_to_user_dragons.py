"""add timeout_notified column to user_dragons

Revision ID: e1e2f3a4b5c7
Revises: d1e2f3a4b5c6
Create Date: 2026-07-03 13:57:00.000000

Добавляет флаг, что уведомление об истечении таймаута уже отправлено.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'e1e2f3a4b5c7'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('user_dragons', schema=None) as batch_op:
        batch_op.add_column(sa.Column('timeout_notified', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    with op.batch_alter_table('user_dragons', schema=None) as batch_op:
        batch_op.drop_column('timeout_notified')
