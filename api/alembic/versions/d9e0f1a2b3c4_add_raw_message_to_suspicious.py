"""add raw_message to suspicious_reports

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-07-08 22:50:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'd9e0f1a2b3c4'
down_revision: Union[str, None] = 'c8d9e0f1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    cols = [c["name"] for c in sa.inspect(op.get_bind()).get_columns("suspicious_reports")]
    if "raw_message" not in cols:
        op.add_column("suspicious_reports", sa.Column("raw_message", sa.Text(), nullable=True, server_default=""))


def downgrade() -> None:
    op.drop_column("suspicious_reports", "raw_message")
