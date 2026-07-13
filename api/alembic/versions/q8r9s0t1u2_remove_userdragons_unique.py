"""remove UniqueConstraint(user_id, dragon_id) from user_dragons

Revision ID: q8r9s0t1u2
Revises: p7q8r9s0t1
Create Date: 2026-07-13 15:41:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'q8r9s0t1u2'
down_revision: Union[str, None] = 'p7q8r9s0t1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE user_dragons_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(vk_id) ON DELETE CASCADE,
            dragon_id INTEGER NOT NULL REFERENCES dragons(id) ON DELETE CASCADE,
            completed_at VARCHAR DEFAULT '',
            next_step_available_at VARCHAR,
            timeout_notified BOOLEAN DEFAULT 0
        )
    """)
    op.execute("""
        INSERT INTO user_dragons_new (id, user_id, dragon_id, completed_at, next_step_available_at, timeout_notified)
        SELECT id, user_id, dragon_id, completed_at, next_step_available_at, timeout_notified
        FROM user_dragons
    """)
    op.execute("DROP TABLE user_dragons")
    op.execute("ALTER TABLE user_dragons_new RENAME TO user_dragons")


def downgrade() -> None:
    op.execute("""
        CREATE TABLE user_dragons_old (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(vk_id) ON DELETE CASCADE,
            dragon_id INTEGER NOT NULL REFERENCES dragons(id) ON DELETE CASCADE,
            completed_at VARCHAR DEFAULT '',
            next_step_available_at VARCHAR,
            timeout_notified BOOLEAN DEFAULT 0,
            UNIQUE(user_id, dragon_id)
        )
    """)
    op.execute("""
        INSERT INTO user_dragons_old (id, user_id, dragon_id, completed_at, next_step_available_at, timeout_notified)
        SELECT id, user_id, dragon_id, completed_at, next_step_available_at, timeout_notified
        FROM user_dragons
    """)
    op.execute("DROP TABLE user_dragons")
    op.execute("ALTER TABLE user_dragons_old RENAME TO user_dragons")
