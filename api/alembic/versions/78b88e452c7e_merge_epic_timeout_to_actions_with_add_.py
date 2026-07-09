"""merge epic_timeout_to_actions with add_image_path_to_epic_stage_actions

Revision ID: 78b88e452c7e
Revises: a0b1c2d3e4f5, e6f7a8b9c0d1
Create Date: 2026-07-09 08:40:38.898834
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa



revision: str = '78b88e452c7e'
down_revision: Union[str, None] = ('a0b1c2d3e4f5', 'e6f7a8b9c0d1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
