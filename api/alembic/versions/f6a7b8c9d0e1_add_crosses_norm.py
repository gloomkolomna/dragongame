"""add crosses_norm to dragon_steps

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-04 21:50:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('dragon_steps', schema=None) as batch_op:
        batch_op.add_column(sa.Column('crosses_norm', sa.Integer(), nullable=True, server_default='1000'))


def downgrade() -> None:
    with op.batch_alter_table('dragon_steps', schema=None) as batch_op:
        batch_op.drop_column('crosses_norm')
