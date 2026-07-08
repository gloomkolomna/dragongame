"""phase 0: epic/shop/legend foundation

Revision ID: c1d2e3f4a5b6
Revises: b6c7d8e9f0a1
Create Date: 2026-07-08 13:10:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, None] = 'b6c7d8e9f0a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('dragons', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_epic', sa.Boolean(), nullable=True, server_default=sa.false()))
        batch_op.add_column(sa.Column('legend_image_path', sa.String(), nullable=True, server_default=''))

    with op.batch_alter_table('dragon_steps', schema=None) as batch_op:
        batch_op.add_column(sa.Column('phase', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('image_path', sa.String(), nullable=True, server_default=''))

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('stitches_balance', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('epic_unlocked', sa.Boolean(), nullable=True, server_default=sa.false()))
        batch_op.add_column(sa.Column('epic_dragon_id', sa.Integer(), nullable=True))

    with op.batch_alter_table('user_progress', schema=None) as batch_op:
        batch_op.add_column(sa.Column('epic_name', sa.String(), nullable=True, server_default=''))

    op.create_table(
        'suspicious_reports',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('dragon_id', sa.Integer(), nullable=True),
        sa.Column('step_number', sa.Integer(), server_default='0'),
        sa.Column('declared_crosses', sa.Integer(), server_default='0'),
        sa.Column('normal_crosses', sa.Integer(), server_default='0'),
        sa.Column('mode', sa.String(), server_default='norm'),
        sa.Column('photo_before_id', sa.Text(), server_default=''),
        sa.Column('photo_after_id', sa.Text(), server_default=''),
        sa.Column('status', sa.String(), server_default='pending'),
        sa.Column('admin_note', sa.Text(), server_default=''),
        sa.Column('created_at', sa.String(), server_default=''),
        sa.ForeignKeyConstraint(['user_id'], ['users.vk_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['dragon_id'], ['dragons.id'], ondelete='SET NULL'),
    )

    op.create_table(
        'shop_items',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), server_default=''),
        sa.Column('cost_stitches', sa.Integer(), server_default='0'),
        sa.Column('category', sa.String(), server_default=''),
        sa.Column('image_path', sa.String(), server_default=''),
        sa.Column('sort_order', sa.Integer(), server_default='0'),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true()),
    )

    op.create_table(
        'stage_shop_items',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('stage_key', sa.String(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('sort_order', sa.Integer(), server_default='0'),
        sa.ForeignKeyConstraint(['item_id'], ['shop_items.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('stage_key', 'item_id'),
    )

    op.create_table(
        'user_inventory',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), server_default='1'),
        sa.Column('acquired_at', sa.String(), server_default=''),
        sa.ForeignKeyConstraint(['user_id'], ['users.vk_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_id'], ['shop_items.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'item_id'),
    )

    op.create_table(
        'epic_stages',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('stage_number', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), server_default=''),
        sa.Column('description', sa.Text(), server_default=''),
        sa.Column('image_path', sa.String(), server_default=''),
        sa.Column('cycles_count', sa.Integer(), server_default='3'),
        sa.Column('care_timeout_hours', sa.Integer(), server_default='24'),
        sa.Column('care_timeout_minutes', sa.Integer(), server_default='0'),
    )

    op.create_table(
        'epic_stage_actions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('stage_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(), server_default=''),
        sa.Column('action_label', sa.String(), server_default=''),
        sa.Column('required_item_id', sa.Integer(), nullable=True),
        sa.Column('order_in_cycle', sa.Integer(), server_default='0'),
        sa.Column('hint', sa.Text(), server_default=''),
        sa.ForeignKeyConstraint(['stage_id'], ['epic_stages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['required_item_id'], ['shop_items.id'], ondelete='SET NULL'),
    )

    op.create_table(
        'epic_care_state',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_dragon_id', sa.Integer(), nullable=False),
        sa.Column('stage_id', sa.Integer(), nullable=True),
        sa.Column('current_action_order', sa.Integer(), server_default='0'),
        sa.Column('next_action_at', sa.String(), nullable=True),
        sa.Column('care_notified', sa.Boolean(), server_default=sa.false()),
        sa.Column('cycles_completed', sa.Integer(), server_default='0'),
        sa.ForeignKeyConstraint(['user_dragon_id'], ['user_dragons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stage_id'], ['epic_stages.id'], ondelete='SET NULL'),
    )

    op.create_table(
        'stage_choice_blocks',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('stage_id', sa.Integer(), nullable=False),
        sa.Column('block_key', sa.String(), server_default=''),
        sa.Column('title', sa.String(), server_default=''),
        sa.Column('prompt_text', sa.Text(), server_default=''),
        sa.Column('choice_type', sa.String(), server_default='single'),
        sa.Column('min_picks', sa.Integer(), server_default='1'),
        sa.Column('max_picks', sa.Integer(), server_default='1'),
        sa.Column('group_limits', sa.Text(), server_default='{}'),
        sa.Column('order_in_stage', sa.Integer(), server_default='0'),
        sa.Column('locked_after_done', sa.Boolean(), server_default=sa.true()),
        sa.ForeignKeyConstraint(['stage_id'], ['epic_stages.id'], ondelete='CASCADE'),
    )

    op.create_table(
        'stage_choice_options',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('block_id', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(), server_default=''),
        sa.Column('group', sa.String(), server_default='neutral'),
        sa.Column('description', sa.Text(), server_default=''),
        sa.Column('image_path', sa.String(), server_default=''),
        sa.ForeignKeyConstraint(['block_id'], ['stage_choice_blocks.id'], ondelete='CASCADE'),
    )

    op.create_table(
        'user_stage_choices',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_dragon_id', sa.Integer(), nullable=False),
        sa.Column('block_id', sa.Integer(), nullable=False),
        sa.Column('option_id', sa.Integer(), nullable=False),
        sa.Column('chosen_at', sa.String(), server_default=''),
        sa.ForeignKeyConstraint(['user_dragon_id'], ['user_dragons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['block_id'], ['stage_choice_blocks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['option_id'], ['stage_choice_options.id'], ondelete='CASCADE'),
    )

    op.create_table(
        'epic_moodlets',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_dragon_id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(), server_default=''),
        sa.Column('title', sa.String(), server_default=''),
        sa.Column('stage_id', sa.Integer(), nullable=True),
        sa.Column('acquired_at', sa.String(), server_default=''),
        sa.ForeignKeyConstraint(['user_dragon_id'], ['user_dragons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['stage_id'], ['epic_stages.id'], ondelete='SET NULL'),
    )


def downgrade() -> None:
    op.drop_table('epic_moodlets')
    op.drop_table('user_stage_choices')
    op.drop_table('stage_choice_options')
    op.drop_table('stage_choice_blocks')
    op.drop_table('epic_care_state')
    op.drop_table('epic_stage_actions')
    op.drop_table('epic_stages')
    op.drop_table('user_inventory')
    op.drop_table('stage_shop_items')
    op.drop_table('shop_items')
    op.drop_table('suspicious_reports')

    with op.batch_alter_table('user_progress', schema=None) as batch_op:
        batch_op.drop_column('epic_name')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('epic_dragon_id')
        batch_op.drop_column('epic_unlocked')
        batch_op.drop_column('stitches_balance')

    with op.batch_alter_table('dragon_steps', schema=None) as batch_op:
        batch_op.drop_column('image_path')
        batch_op.drop_column('phase')

    with op.batch_alter_table('dragons', schema=None) as batch_op:
        batch_op.drop_column('legend_image_path')
        batch_op.drop_column('is_epic')
