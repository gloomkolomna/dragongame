"""epic stages become per-dragon; bind existing stages + shop keys to dragon 64

Revision ID: n5o6p7q8r9s0
Revises: m4n5b6c7d8e9
Create Date: 2026-07-12 18:40:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'n5o6p7q8r9s0'
down_revision: Union[str, None] = 'm4n5b6c7d8e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEGACY_DRAGON_ID = 64


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c['name'] for c in insp.get_columns('epic_stages')}
    if 'dragon_id' not in cols:
        with op.batch_alter_table('epic_stages', schema=None) as batch_op:
            batch_op.add_column(sa.Column('dragon_id', sa.Integer(), nullable=False, server_default='0'))
        bind.execute(sa.text("UPDATE epic_stages SET dragon_id = :did"), {"did": LEGACY_DRAGON_ID})
        with op.batch_alter_table('epic_stages', schema=None) as batch_op:
            batch_op.alter_column('dragon_id', server_default=None)

    stages = bind.execute(
        sa.text("SELECT id, dragon_id, stage_number FROM epic_stages")
    ).fetchall()
    for row in stages:
        old_key = f"epic:{row.stage_number}"
        new_key = f"epic:{row.dragon_id}:{row.stage_number}"
        bind.execute(
            sa.text(
                "UPDATE OR IGNORE stage_shop_items SET stage_key = :new WHERE stage_key = :old"
            ),
            {"new": new_key, "old": old_key},
        )

    bind.execute(
        sa.text(
            "UPDATE OR IGNORE stage_shop_items SET stage_key = :new WHERE stage_key = :old"
        ),
        {"new": f"epic:{LEGACY_DRAGON_ID}:egg", "old": "epic:egg"},
    )


def downgrade() -> None:
    bind = op.get_bind()
    stages = bind.execute(
        sa.text("SELECT id, dragon_id, stage_number FROM epic_stages")
    ).fetchall()
    for row in stages:
        old_key = f"epic:{row.dragon_id}:{row.stage_number}"
        new_key = f"epic:{row.stage_number}"
        bind.execute(
            sa.text(
                "UPDATE OR IGNORE stage_shop_items SET stage_key = :new WHERE stage_key = :old"
            ),
            {"new": new_key, "old": old_key},
        )
    with op.batch_alter_table('epic_stages', schema=None) as batch_op:
        batch_op.drop_column('dragon_id')
