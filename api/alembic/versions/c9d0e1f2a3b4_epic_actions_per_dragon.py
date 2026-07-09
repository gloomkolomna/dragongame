"""epic stage actions become per-dragon

Revision ID: c9d0e1f2a3b4
Revises: f2e3d4c5b6a7
Create Date: 2026-07-09 18:40:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, None] = 'f2e3d4c5b6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM epic_action_items"))
    bind.execute(sa.text("DELETE FROM epic_stage_actions"))
    insp = sa.inspect(bind)
    cols = {c['name'] for c in insp.get_columns('epic_stage_actions')}
    if 'dragon_id' not in cols:
        with op.batch_alter_table('epic_stage_actions', schema=None) as batch_op:
            batch_op.add_column(sa.Column('dragon_id', sa.Integer(), nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('epic_stage_actions', schema=None) as batch_op:
        batch_op.drop_column('dragon_id')
