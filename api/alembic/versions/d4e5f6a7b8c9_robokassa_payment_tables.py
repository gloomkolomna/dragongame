"""robokassa payment tables

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-09 15:30:00.000000
"""
from typing import Sequence, Union
from datetime import datetime
from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('pricing_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('base_price_per_dragon', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('dragon_sets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('discount_percent', sa.Integer(), nullable=True),
        sa.Column('donor_discount_percent', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('payment_orders',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('vk_id', sa.Integer(), nullable=False),
        sa.Column('set_id', sa.Integer(), nullable=True),
        sa.Column('amount_rub', sa.Integer(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.Column('price_per_pin', sa.Integer(), nullable=True),
        sa.Column('robokassa_inv_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('dragon_ids', sa.Text(), nullable=True),
        sa.Column('notified', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=True),
        sa.Column('completed_at', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['vk_id'], ['users.vk_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['set_id'], ['dragon_sets.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    op.execute(
        "INSERT INTO pricing_config (id, base_price_per_dragon, updated_at) "
        f"VALUES (1, 10000, '{now}')"
    )


def downgrade() -> None:
    op.drop_table('payment_orders')
    op.drop_table('dragon_sets')
    op.drop_table('pricing_config')
