"""drop epic_cost_stitches from dragons (removed incubator feature)"""

import sqlalchemy as sa
from alembic import op

revision = "u1v2w3x4y5z6"
down_revision = "j9k0l1m2n3o4"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = [c["name"] for c in inspector.get_columns("dragons")]
    if "epic_cost_stitches" in cols:
        with op.batch_alter_table("dragons") as batch_op:
            batch_op.drop_column("epic_cost_stitches")


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = [c["name"] for c in inspector.get_columns("dragons")]
    if "epic_cost_stitches" not in cols:
        with op.batch_alter_table("dragons") as batch_op:
            batch_op.add_column(sa.Column("epic_cost_stitches", sa.Integer(), nullable=True))
