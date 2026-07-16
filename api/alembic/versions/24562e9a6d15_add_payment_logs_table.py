"""add payment logs table

Revision ID: 24562e9a6d15
Revises: n6o7p8q9r0s1
Create Date: 2026-07-16 15:52:38.126943
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '24562e9a6d15'
down_revision: Union[str, None] = 'n6o7p8q9r0s1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('payment_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('vk_id', sa.Integer(), nullable=True),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=30), nullable=True),
        sa.Column('login', sa.String(), nullable=True),
        sa.Column('out_sum', sa.String(), nullable=True),
        sa.Column('inv_id', sa.String(), nullable=True),
        sa.Column('test_mode', sa.Boolean(), nullable=True),
        sa.Column('sig', sa.String(), nullable=True),
        sa.Column('receipt_json', sa.Text(), nullable=True),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('payment_logs')
