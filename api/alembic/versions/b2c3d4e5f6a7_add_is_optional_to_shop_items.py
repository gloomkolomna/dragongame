"""add is_optional to shop_items

Revision ID: b2c3d4e5f6a7
Revises: 78b88e452c7e
Create Date: 2026-07-09 10:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = '78b88e452c7e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('shop_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_optional', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    with op.batch_alter_table('shop_items', schema=None) as batch_op:
        batch_op.drop_column('is_optional')
