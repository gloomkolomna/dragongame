"""extend pin_code from 4 to 5 chars

Revision ID: f1a2b3c4d5e6
Revises: e1e2f3a4b5c7
Create Date: 2026-07-03 18:33:00.000000

Изменяет длину pin_code с 4 до 5 символов для поддержки
нового формата: заглавные латинские буквы (A-Z) + цифры (0-9).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e1e2f3a4b5c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('dragons', schema=None) as batch_op:
        batch_op.alter_column('pin_code',
                              existing_type=sa.String(length=4),
                              type_=sa.String(length=5),
                              existing_nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('dragons', schema=None) as batch_op:
        batch_op.alter_column('pin_code',
                              existing_type=sa.String(length=5),
                              type_=sa.String(length=4),
                              existing_nullable=True)
