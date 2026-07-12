"""add image_path to epic_moodlets

Revision ID: m4n5b6c7d8e9
Revises: l3f4a5b6c7d8
Create Date: 2026-07-12 17:44:24.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "m4n5b6c7d8e9"
down_revision = "l3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("epic_moodlets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("image_path", sa.String(), server_default="", nullable=False))


def downgrade():
    with op.batch_alter_table("epic_moodlets", schema=None) as batch_op:
        batch_op.drop_column("image_path")
