"""add finale_description to dragons

Revision ID: j9k0l1m2n3o4
Revises: h5i6j7k8l9m0
Create Date: 2026-07-14 08:36:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'j9k0l1m2n3o4'
down_revision: Union[str, None] = 'h5i6j7k8l9m0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('dragons', sa.Column('finale_description', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('dragons', 'finale_description')
