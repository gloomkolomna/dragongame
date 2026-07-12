"""add epic_action_outcomes + action random_outcome/character_axis_id

Revision ID: j1d2e3f4a5b6
Revises: i0c1d2e3f4a5
Create Date: 2026-07-12 09:40:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'j1d2e3f4a5b6'
down_revision: Union[str, None] = 'i0c1d2e3f4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('epic_stage_actions') as batch:
        batch.add_column(sa.Column('random_outcome', sa.Boolean(), nullable=True, server_default=sa.text('1')))
        batch.add_column(sa.Column('character_axis_id', sa.Integer(), nullable=True))

    op.create_table(
        'epic_action_outcomes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('action_id', sa.Integer(), nullable=False),
        sa.Column('polarity', sa.String(), nullable=True, server_default='positive'),
        sa.Column('label', sa.String(), nullable=True, server_default=''),
        sa.Column('moodlet_title', sa.String(), nullable=True, server_default=''),
        sa.Column('moodlet_text', sa.Text(), nullable=True, server_default=''),
        sa.Column('image_path', sa.String(), nullable=True, server_default=''),
        sa.ForeignKeyConstraint(['action_id'], ['epic_stage_actions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('action_id', 'polarity'),
    )


def downgrade() -> None:
    op.drop_table('epic_action_outcomes')
    with op.batch_alter_table('epic_stage_actions') as batch:
        batch.drop_column('character_axis_id')
        batch.drop_column('random_outcome')
