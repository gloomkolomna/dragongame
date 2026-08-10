"""remove selfwork provider, add moneta

Revision ID: m1n2o3p4q5r6
Revises: sw1a2b3c4d5e
Create Date: 2026-08-10 16:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'm1n2o3p4q5r6'
down_revision: Union[str, None] = 'sw1a2b3c4d5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('payment_orders', schema=None) as batch_op:
        batch_op.drop_column('selfwork_order_id')


def downgrade() -> None:
    with op.batch_alter_table('payment_orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('selfwork_order_id', sa.String(), nullable=True))
