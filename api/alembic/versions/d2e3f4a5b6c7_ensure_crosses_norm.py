"""ensure phase-0 columns exist (repair drift: crosses_norm)

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-07-08 13:55:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'd2e3f4a5b6c7'
down_revision: Union[str, None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cols(table: str) -> set:
    bind = op.get_bind()
    return {c['name'] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    steps = _cols('dragon_steps')
    with op.batch_alter_table('dragon_steps', schema=None) as batch_op:
        if 'crosses_norm' not in steps:
            batch_op.add_column(sa.Column('crosses_norm', sa.Integer(), nullable=True, server_default='1000'))
        if 'phase' not in steps:
            batch_op.add_column(sa.Column('phase', sa.Integer(), nullable=True, server_default='0'))
        if 'image_path' not in steps:
            batch_op.add_column(sa.Column('image_path', sa.String(), nullable=True, server_default=''))


def downgrade() -> None:
    pass
