"""shop character_effect, multi-item care actions

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-07-08 15:05:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'f4a5b6c7d8e9'
down_revision: Union[str, None] = 'e3f4a5b6c7d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('shop_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('character_effect', sa.String(), nullable=True, server_default=''))

    op.create_table(
        'epic_action_items',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('action_id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['action_id'], ['epic_stage_actions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_id'], ['shop_items.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('action_id', 'item_id'),
    )

    bind = op.get_bind()
    cols = {c['name'] for c in sa.inspect(bind).get_columns('epic_stage_actions')}
    if 'required_item_id' in cols:
        op.execute(
            "INSERT INTO epic_action_items (action_id, item_id) "
            "SELECT id, required_item_id FROM epic_stage_actions WHERE required_item_id IS NOT NULL"
        )
        with op.batch_alter_table('epic_stage_actions', schema=None) as batch_op:
            batch_op.drop_column('required_item_id')


def downgrade() -> None:
    with op.batch_alter_table('epic_stage_actions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('required_item_id', sa.Integer(), nullable=True))
    op.drop_table('epic_action_items')
    with op.batch_alter_table('shop_items', schema=None) as batch_op:
        batch_op.drop_column('character_effect')
