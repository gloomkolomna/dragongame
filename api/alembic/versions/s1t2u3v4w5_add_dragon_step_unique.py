"""add UniqueConstraint(dragon_id, step_number, phase) on dragon_steps

Revision ID: s1t2u3v4w5
Revises: r9s0t1u2v3
Create Date: 2026-07-13 17:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 's1t2u3v4w5'
down_revision: Union[str, None] = 'r9s0t1u2v3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DELETE FROM dragon_steps
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM dragon_steps
            GROUP BY dragon_id, step_number, phase
        )
    """)
    with op.batch_alter_table('dragon_steps', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_dragon_steps_step', ['dragon_id', 'step_number', 'phase'])


def downgrade() -> None:
    with op.batch_alter_table('dragon_steps', schema=None) as batch_op:
        batch_op.drop_constraint('uq_dragon_steps_step', type_='unique')
