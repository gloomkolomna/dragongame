"""add legend_title and legend_full_text to dragons

Revision ID: f0a1b2c3d4e5
Revises: d9e0f1a2b3c4
Create Date: 2026-07-08 23:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'f0a1b2c3d4e5'
down_revision: Union[str, None] = 'd9e0f1a2b3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c['name'] for c in insp.get_columns('dragons')}
    with op.batch_alter_table('dragons', schema=None) as batch_op:
        if 'legend_title' not in cols:
            batch_op.add_column(sa.Column('legend_title', sa.String(), server_default=''))
        if 'legend_full_text' not in cols:
            batch_op.add_column(sa.Column('legend_full_text', sa.Text(), server_default=''))


def downgrade() -> None:
    with op.batch_alter_table('dragons', schema=None) as batch_op:
        batch_op.drop_column('legend_full_text')
        batch_op.drop_column('legend_title')
