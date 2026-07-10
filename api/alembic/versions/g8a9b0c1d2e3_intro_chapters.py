"""add intro_chapters table

Revision ID: g8a9b0c1d2e3
Revises: f7a8b9c0d1e2
Create Date: 2026-07-10 19:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'g8a9b0c1d2e3'
down_revision: Union[str, None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'intro_chapters',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('chapter_number', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=True, server_default=''),
        sa.Column('image_path', sa.String(), nullable=True, server_default=''),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('1')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chapter_number'),
    )


def downgrade() -> None:
    op.drop_table('intro_chapters')
