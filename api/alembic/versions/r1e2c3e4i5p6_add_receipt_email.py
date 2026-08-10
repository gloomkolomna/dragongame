"""add receipt_email to payment_orders

Revision ID: r1e2c3e4i5p6
Revises: t1e2s3t4m5o6
Create Date: 2026-08-10 18:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'r1e2c3e4i5p6'
down_revision: Union[str, None] = 't1e2s3t4m5o6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('payment_orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('receipt_email', sa.String(length=128), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('payment_orders', schema=None) as batch_op:
        batch_op.drop_column('receipt_email')
