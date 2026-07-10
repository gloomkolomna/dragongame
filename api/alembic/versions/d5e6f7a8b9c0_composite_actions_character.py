"""composite epic actions + character axes + moodlet polarity

Revision ID: d5e6f7a8b9c0
Revises: c9d0e1f2a3b4
Create Date: 2026-07-10 11:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if 'character_axes' not in insp.get_table_names():
        op.create_table(
            'character_axes',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('positive_label', sa.String(), server_default=''),
            sa.Column('negative_label', sa.String(), server_default=''),
            sa.Column('sort_order', sa.Integer(), server_default='0'),
            sa.Column('is_active', sa.Boolean(), server_default='1'),
        )

    if 'character_balance' not in insp.get_table_names():
        op.create_table(
            'character_balance',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('user_dragon_id', sa.Integer(), nullable=False),
            sa.Column('axis_id', sa.Integer(), nullable=False),
            sa.Column('score', sa.Integer(), server_default='0'),
            sa.ForeignKeyConstraint(['user_dragon_id'], ['user_dragons.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['axis_id'], ['character_axes.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('user_dragon_id', 'axis_id'),
        )

    if 'epic_sub_actions' not in insp.get_table_names():
        op.create_table(
            'epic_sub_actions',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('action_id', sa.Integer(), nullable=False),
            sa.Column('label', sa.String(), server_default=''),
            sa.Column('description', sa.Text(), server_default=''),
            sa.Column('order_in_sub', sa.Integer(), server_default='0'),
            sa.Column('image_path', sa.String(), server_default=''),
            sa.Column('character_axis_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['action_id'], ['epic_stage_actions.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['character_axis_id'], ['character_axes.id'], ondelete='SET NULL'),
            sa.UniqueConstraint('action_id', 'label'),
        )

    if 'epic_sub_action_items' not in insp.get_table_names():
        op.create_table(
            'epic_sub_action_items',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('sub_action_id', sa.Integer(), nullable=False),
            sa.Column('item_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['sub_action_id'], ['epic_sub_actions.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['item_id'], ['shop_items.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('sub_action_id', 'item_id'),
        )

    if 'epic_sub_action_steps' not in insp.get_table_names():
        op.create_table(
            'epic_sub_action_steps',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('sub_action_id', sa.Integer(), nullable=False),
            sa.Column('step_label', sa.String(), server_default=''),
            sa.Column('order', sa.Integer(), server_default='0'),
            sa.Column('task', sa.Text(), server_default=''),
            sa.Column('hint', sa.Text(), server_default=''),
            sa.Column('crosses_norm', sa.Integer(), server_default='1000'),
            sa.Column('image_path', sa.String(), server_default=''),
            sa.Column('timeout_hours', sa.Integer(), server_default='24'),
            sa.Column('timeout_minutes', sa.Integer(), server_default='0'),
            sa.ForeignKeyConstraint(['sub_action_id'], ['epic_sub_actions.id'], ondelete='CASCADE'),
        )

    if 'epic_sub_action_outcomes' not in insp.get_table_names():
        op.create_table(
            'epic_sub_action_outcomes',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('sub_action_id', sa.Integer(), nullable=False),
            sa.Column('polarity', sa.String(), server_default='positive'),
            sa.Column('label', sa.String(), server_default=''),
            sa.Column('moodlet_title', sa.String(), server_default=''),
            sa.Column('moodlet_text', sa.Text(), server_default=''),
            sa.Column('image_path', sa.String(), server_default=''),
            sa.ForeignKeyConstraint(['sub_action_id'], ['epic_sub_actions.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('sub_action_id', 'polarity'),
        )

    ec_cols = {c['name'] for c in insp.get_columns('epic_stage_actions')}
    if 'action_type' not in ec_cols:
        with op.batch_alter_table('epic_stage_actions', schema=None) as batch_op:
            batch_op.add_column(sa.Column('action_type', sa.String(), nullable=True, server_default='simple'))

    si_cols = {c['name'] for c in insp.get_columns('shop_items')}
    if 'is_consumable' not in si_cols:
        with op.batch_alter_table('shop_items', schema=None) as batch_op:
            batch_op.add_column(sa.Column('is_consumable', sa.Boolean(), nullable=True, server_default='1'))
    if 'character_effect' in si_cols:
        with op.batch_alter_table('shop_items', schema=None) as batch_op:
            batch_op.drop_column('character_effect')

    em_cols = {c['name'] for c in insp.get_columns('epic_moodlets')}
    if 'polarity' not in em_cols:
        with op.batch_alter_table('epic_moodlets', schema=None) as batch_op:
            batch_op.add_column(sa.Column('polarity', sa.String(), nullable=True, server_default='positive'))
    if 'text' not in em_cols:
        with op.batch_alter_table('epic_moodlets', schema=None) as batch_op:
            batch_op.add_column(sa.Column('text', sa.Text(), nullable=True, server_default=''))
    if 'axis_id' not in em_cols:
        with op.batch_alter_table('epic_moodlets', schema=None) as batch_op:
            batch_op.add_column(sa.Column('axis_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                'fk_epic_moodlets_axis_id',
                'character_axes', ['axis_id'], ['id'],
                ondelete='SET NULL',
            )

    cs_cols = {c['name'] for c in insp.get_columns('epic_care_state')}
    if 'current_sub_action_id' not in cs_cols:
        with op.batch_alter_table('epic_care_state', schema=None) as batch_op:
            batch_op.add_column(sa.Column('current_sub_action_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                'fk_epic_care_state_sub_action',
                'epic_sub_actions', ['current_sub_action_id'], ['id'],
                ondelete='SET NULL',
            )
    if 'current_step_order' not in cs_cols:
        with op.batch_alter_table('epic_care_state', schema=None) as batch_op:
            batch_op.add_column(sa.Column('current_step_order', sa.Integer(), nullable=True, server_default='0'))
    if 'sub_had_penalty' not in cs_cols:
        with op.batch_alter_table('epic_care_state', schema=None) as batch_op:
            batch_op.add_column(sa.Column('sub_had_penalty', sa.Boolean(), nullable=True, server_default='0'))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    cs_cols = {c['name'] for c in insp.get_columns('epic_care_state')}
    with op.batch_alter_table('epic_care_state', schema=None) as batch_op:
        if 'current_sub_action_id' in cs_cols:
            batch_op.drop_constraint('fk_epic_care_state_sub_action', type_='foreignkey')
            batch_op.drop_column('current_sub_action_id')
        if 'current_step_order' in cs_cols:
            batch_op.drop_column('current_step_order')
        if 'sub_had_penalty' in cs_cols:
            batch_op.drop_column('sub_had_penalty')

    em_cols = {c['name'] for c in insp.get_columns('epic_moodlets')}
    with op.batch_alter_table('epic_moodlets', schema=None) as batch_op:
        if 'axis_id' in em_cols:
            batch_op.drop_constraint('fk_epic_moodlets_axis_id', type_='foreignkey')
            batch_op.drop_column('axis_id')
        if 'text' in em_cols:
            batch_op.drop_column('text')
        if 'polarity' in em_cols:
            batch_op.drop_column('polarity')

    si_cols = {c['name'] for c in insp.get_columns('shop_items')}
    with op.batch_alter_table('shop_items', schema=None) as batch_op:
        if 'character_effect' not in si_cols:
            batch_op.add_column(sa.Column('character_effect', sa.String(), nullable=True, server_default=''))
        if 'is_consumable' in si_cols:
            batch_op.drop_column('is_consumable')

    ec_cols = {c['name'] for c in insp.get_columns('epic_stage_actions')}
    if 'action_type' in ec_cols:
        with op.batch_alter_table('epic_stage_actions', schema=None) as batch_op:
            batch_op.drop_column('action_type')

    tables = insp.get_table_names()
    for t in ['epic_sub_action_outcomes', 'epic_sub_action_steps', 'epic_sub_action_items',
              'epic_sub_actions', 'character_balance', 'character_axes']:
        if t in tables:
            op.drop_table(t)
