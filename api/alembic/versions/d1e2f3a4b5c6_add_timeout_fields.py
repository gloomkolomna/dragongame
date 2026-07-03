"""add timeout_hours/timeout_minutes to dragon_steps, next_step_available_at to user_dragons

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-07-03 13:53:32.000000

Добавляет поддержку таймаутов между шагами выращивания драконов.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'c0d1e2f3a4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('dragon_steps', schema=None) as batch_op:
        batch_op.add_column(sa.Column('timeout_hours', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('timeout_minutes', sa.Integer(), nullable=False, server_default='0'))

    with op.batch_alter_table('user_dragons', schema=None) as batch_op:
        batch_op.add_column(sa.Column('next_step_available_at', sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('user_dragons', schema=None) as batch_op:
        batch_op.drop_column('next_step_available_at')

    with op.batch_alter_table('dragon_steps', schema=None) as batch_op:
        batch_op.drop_column('timeout_minutes')
        batch_op.drop_column('timeout_hours')
