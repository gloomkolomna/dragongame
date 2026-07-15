"""add sort_order to dragon_sets"""

import sqlalchemy as sa
from alembic import op

revision = "k3l4m5n6o7p8"
down_revision = "u1v2w3x4y5z6"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = [c["name"] for c in inspector.get_columns("dragon_sets")]
    if "sort_order" not in cols:
        with op.batch_alter_table("dragon_sets") as batch_op:
            batch_op.add_column(sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
        op.execute("UPDATE dragon_sets SET sort_order = id")


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = [c["name"] for c in inspector.get_columns("dragon_sets")]
    if "sort_order" in cols:
        with op.batch_alter_table("dragon_sets") as batch_op:
            batch_op.drop_column("sort_order")
