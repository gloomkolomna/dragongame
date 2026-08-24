"""payment_orders.gateway_txn_id (pay-gateway)

Revision ID: b7c8d9e0f1a2
Revises: v1d2o3n4c5a6
Create Date: 2026-08-24 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, None] = 'v1d2o3n4c5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('payment_orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('gateway_txn_id', sa.String(length=32), nullable=True))
        batch_op.create_index('ix_payment_orders_gateway_txn_id', ['gateway_txn_id'], unique=True)


def downgrade() -> None:
    with op.batch_alter_table('payment_orders', schema=None) as batch_op:
        batch_op.drop_index('ix_payment_orders_gateway_txn_id')
        batch_op.drop_column('gateway_txn_id')
