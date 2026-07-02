"""add color to families

Revision ID: a1b2c3d4e5f6
Revises: 359d89020f12
Create Date: 2026-07-02 12:34:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '359d89020f12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('families', schema=None) as batch_op:
        batch_op.add_column(sa.Column('color', sa.String(length=7), nullable=True, server_default='#9b6fc7'))


def downgrade() -> None:
    with op.batch_alter_table('families', schema=None) as batch_op:
        batch_op.drop_column('color')
