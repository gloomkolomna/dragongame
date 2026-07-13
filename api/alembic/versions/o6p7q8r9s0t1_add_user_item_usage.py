"""add user_item_usage table

Revision ID: o6p7q8r9s0t1
Revises: n5o6p7q8r9s0
Create Date: 2026-07-13 10:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'o6p7q8r9s0t1'
down_revision: Union[str, None] = 'n5o6p7q8r9s0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_item_usage (
            id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            user_dragon_id INTEGER NOT NULL,
            used_at VARCHAR,
            PRIMARY KEY (id),
            UNIQUE (user_id, item_id, user_dragon_id),
            FOREIGN KEY (user_id) REFERENCES users (vk_id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES shop_items (id) ON DELETE CASCADE,
            FOREIGN KEY (user_dragon_id) REFERENCES user_dragons (id) ON DELETE CASCADE
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_item_usage")
