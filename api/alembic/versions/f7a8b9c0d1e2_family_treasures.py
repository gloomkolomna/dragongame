"""add family_id to treasures, make dragon_id nullable

Revision ID: f7a8b9c0d1e2
Revises: d5e6f7a8b9c0
Create Date: 2026-07-10 18:45:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, None] = 'd5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c['name'] for c in insp.get_columns('treasures')}
    with op.batch_alter_table('treasures', schema=None) as batch_op:
        if 'family_id' not in cols:
            batch_op.add_column(sa.Column('family_id', sa.Integer(), nullable=True, server_default=None))
            batch_op.create_foreign_key('fk_treasure_family', 'families', ['family_id'], ['id'], ondelete='CASCADE')
        if 'dragon_id' in cols:
            batch_op.alter_column('dragon_id', nullable=True)


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c['name'] for c in insp.get_columns('treasures')}
    with op.batch_alter_table('treasures', schema=None) as batch_op:
        if 'family_id' in cols:
            batch_op.drop_constraint('fk_treasure_family', type_='foreignkey')
            batch_op.drop_column('family_id')
        if 'dragon_id' in cols:
            batch_op.alter_column('dragon_id', nullable=False)
