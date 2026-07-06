"""add image_path to families

Revision ID: b6c7d8e9f0a1
Revises: a1b2c3d4e5f6
Create Date: 2026-07-06 11:55:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'b6c7d8e9f0a1'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('families', schema=None) as batch_op:
        batch_op.add_column(sa.Column('image_path', sa.String(), nullable=True, server_default=''))


def downgrade() -> None:
    with op.batch_alter_table('families', schema=None) as batch_op:
        batch_op.drop_column('image_path')
