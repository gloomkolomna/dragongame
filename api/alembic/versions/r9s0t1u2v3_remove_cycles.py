"""remove cycles_count from epic_stages and cycles_completed from epic_care_state

Revision ID: r9s0t1u2v3
Revises: q8r9s0t1u2
Create Date: 2026-07-13 15:50:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'r9s0t1u2v3'
down_revision: Union[str, None] = 'q8r9s0t1u2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE epic_stages_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dragon_id INTEGER NOT NULL REFERENCES dragons(id) ON DELETE CASCADE,
            stage_number INTEGER NOT NULL,
            name VARCHAR DEFAULT '',
            description TEXT DEFAULT '',
            image_path VARCHAR DEFAULT '',
            image_start VARCHAR DEFAULT '',
            image_end VARCHAR DEFAULT ''
        )
    """)
    op.execute("""
        INSERT INTO epic_stages_new (id, dragon_id, stage_number, name, description, image_path, image_start, image_end)
        SELECT id, dragon_id, stage_number, name, description, image_path, image_start, image_end
        FROM epic_stages
    """)
    op.execute("DROP TABLE epic_stages")
    op.execute("ALTER TABLE epic_stages_new RENAME TO epic_stages")

    op.execute("""
        CREATE TABLE epic_care_state_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_dragon_id INTEGER NOT NULL REFERENCES user_dragons(id) ON DELETE CASCADE,
            stage_id INTEGER REFERENCES epic_stages(id) ON DELETE SET NULL,
            current_action_order INTEGER DEFAULT 0,
            current_sub_action_id INTEGER REFERENCES epic_sub_actions(id) ON DELETE SET NULL,
            current_step_order INTEGER DEFAULT 0,
            sub_had_penalty BOOLEAN DEFAULT 0,
            next_action_at VARCHAR,
            care_notified BOOLEAN DEFAULT 0
        )
    """)
    op.execute("""
        INSERT INTO epic_care_state_new (id, user_dragon_id, stage_id, current_action_order, current_sub_action_id, current_step_order, sub_had_penalty, next_action_at, care_notified)
        SELECT id, user_dragon_id, stage_id, current_action_order, current_sub_action_id, current_step_order, sub_had_penalty, next_action_at, care_notified
        FROM epic_care_state
    """)
    op.execute("DROP TABLE epic_care_state")
    op.execute("ALTER TABLE epic_care_state_new RENAME TO epic_care_state")


def downgrade() -> None:
    op.execute("ALTER TABLE epic_stages ADD COLUMN cycles_count INTEGER DEFAULT 3")
    op.execute("ALTER TABLE epic_care_state ADD COLUMN cycles_completed INTEGER DEFAULT 0")
