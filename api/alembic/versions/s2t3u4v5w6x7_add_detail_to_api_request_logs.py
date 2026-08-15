"""add query_params, request_body, response_detail to api_request_logs

Revision ID: s2t3u4v5w6x7
Revises: r1e2c3e4i5p6
Create Date: 2026-08-15 11:40:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 's2t3u4v5w6x7'
down_revision: Union[str, None] = 'r1e2c3e4i5p6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('api_request_logs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('query_params', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('request_body', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('response_detail', sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('api_request_logs', schema=None) as batch_op:
        batch_op.drop_column('response_detail')
        batch_op.drop_column('request_body')
        batch_op.drop_column('query_params')
