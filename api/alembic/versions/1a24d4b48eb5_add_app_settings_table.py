"""add_app_settings_table

Revision ID: 1a24d4b48eb5
Revises: a8b9c0d1e2f3
Create Date: 2026-07-28 20:12:25.811904
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '1a24d4b48eb5'
down_revision: Union[str, None] = 'a8b9c0d1e2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('app_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('welcome_keyword', sa.String(), nullable=True),
    sa.Column('updated_at', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('app_settings')
