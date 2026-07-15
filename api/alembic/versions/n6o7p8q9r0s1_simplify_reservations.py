"""simplify dragon_reservations: replace status with is_activated, add vk_name

Revision ID: n6o7p8q9r0s1
Revises: m5n6o7p8q9r0
Create Date: 2026-07-15 22:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'n6o7p8q9r0s1'
down_revision: Union[str, None] = 'm5n6o7p8q9r0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('dragon_reservations', sa.Column('is_activated', sa.Boolean(), nullable=True, server_default=sa.text('0')))
    op.add_column('dragon_reservations', sa.Column('activated_at', sa.String(), nullable=True, server_default=None))
    op.add_column('dragon_reservations', sa.Column('vk_name', sa.String(), nullable=True, server_default=''))
    op.drop_column('dragon_reservations', 'status')


def downgrade() -> None:
    op.add_column('dragon_reservations', sa.Column('status', sa.String(20), nullable=True, server_default='reserved'))
    op.drop_column('dragon_reservations', 'is_activated')
    op.drop_column('dragon_reservations', 'activated_at')
    op.drop_column('dragon_reservations', 'vk_name')
