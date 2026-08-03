"""add payment provider

Revision ID: sw1a2b3c4d5e
Revises: 5f87cfc10ebb
Create Date: 2026-08-03 22:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'sw1a2b3c4d5e'
down_revision: Union[str, None] = '5f87cfc10ebb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('app_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('payment_provider', sa.String(), nullable=True, server_default='robokassa'))
    with op.batch_alter_table('payment_orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('provider', sa.String(), nullable=True, server_default='robokassa'))
        batch_op.add_column(sa.Column('selfwork_order_id', sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('payment_orders', schema=None) as batch_op:
        batch_op.drop_column('selfwork_order_id')
        batch_op.drop_column('provider')
    with op.batch_alter_table('app_settings', schema=None) as batch_op:
        batch_op.drop_column('payment_provider')
