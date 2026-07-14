"""add finale_image_path to dragons

Revision ID: h5i6j7k8l9m0
Revises: g3h4i5j6k7l8
Create Date: 2026-07-14 08:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'h5i6j7k8l9m0'
down_revision: Union[str, None] = 'g3h4i5j6k7l8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('dragons', sa.Column('finale_image_path', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('dragons', 'finale_image_path')
