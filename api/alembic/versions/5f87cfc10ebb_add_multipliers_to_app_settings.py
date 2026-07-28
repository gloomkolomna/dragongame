"""add_multipliers_to_app_settings

Revision ID: 5f87cfc10ebb
Revises: 1a24d4b48eb5
Create Date: 2026-07-28 20:22:04.418517
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '5f87cfc10ebb'
down_revision: Union[str, None] = '1a24d4b48eb5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('app_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('suspicious_multiplier', sa.Integer(), nullable=True, server_default='2'))
        batch_op.add_column(sa.Column('block_multiplier', sa.Integer(), nullable=True, server_default='3'))


def downgrade() -> None:
    with op.batch_alter_table('app_settings', schema=None) as batch_op:
        batch_op.drop_column('block_multiplier')
        batch_op.drop_column('suspicious_multiplier')
