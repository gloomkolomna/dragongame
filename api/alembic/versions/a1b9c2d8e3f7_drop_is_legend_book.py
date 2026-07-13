"""drop is_legend_book from shop_items"""

import sqlalchemy as sa
from alembic import op

revision = "a1b9c2d8e3f7"
down_revision = "s1t2u3v4w5"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = [c["name"] for c in inspector.get_columns("shop_items")]
    if "is_legend_book" in cols:
        with op.batch_alter_table("shop_items") as batch_op:
            batch_op.drop_column("is_legend_book")


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = [c["name"] for c in inspector.get_columns("shop_items")]
    if "is_legend_book" not in cols:
        with op.batch_alter_table("shop_items") as batch_op:
            batch_op.add_column(sa.Column("is_legend_book", sa.Boolean(), nullable=True, server_default="0"))
