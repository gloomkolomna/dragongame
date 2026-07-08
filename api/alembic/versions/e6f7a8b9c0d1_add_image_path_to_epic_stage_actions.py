"""add image_path to epic_stage_actions

Revision ID: e6f7a8b9c0d1
Revises: f0a1b2c3d4e5
Create Date: 2026-07-09 00:22:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'e6f7a8b9c0d1'
down_revision: Union[str, None] = 'f0a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c['name'] for c in insp.get_columns('epic_stage_actions')}
    if 'image_path' not in cols:
        with op.batch_alter_table('epic_stage_actions', schema=None) as batch_op:
            batch_op.add_column(sa.Column('image_path', sa.String(), server_default=''))


def downgrade() -> None:
    with op.batch_alter_table('epic_stage_actions', schema=None) as batch_op:
        batch_op.drop_column('image_path')
