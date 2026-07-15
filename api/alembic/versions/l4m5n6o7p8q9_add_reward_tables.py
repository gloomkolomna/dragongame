"""add reward_configs and user_reward_pins tables"""

import sqlalchemy as sa
from alembic import op

revision = "l4m5n6o7p8q9"
down_revision = "k3l4m5n6o7p8"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "reward_configs" not in tables:
        op.create_table(
            "reward_configs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_type", sa.String(20), nullable=False, server_default="donor"),
            sa.Column("eggs_per_period", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("period_days", sa.Integer(), nullable=False, server_default="30"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("rarity_filter", sa.String(), nullable=False, server_default=""),
            sa.Column("created_at", sa.String(), nullable=False, server_default=""),
            sa.Column("updated_at", sa.String(), nullable=False, server_default=""),
        )

    if "user_reward_pins" not in tables:
        op.create_table(
            "user_reward_pins",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.vk_id", ondelete="CASCADE"), nullable=False),
            sa.Column("dragon_id", sa.Integer(), sa.ForeignKey("dragons.id", ondelete="SET NULL"), nullable=True),
            sa.Column("pin_code", sa.String(5), nullable=False, server_default=""),
            sa.Column("config_id", sa.Integer(), sa.ForeignKey("reward_configs.id", ondelete="SET NULL"), nullable=True),
            sa.Column("issued_at", sa.String(), nullable=False, server_default=""),
            sa.Column("activated", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("activated_at", sa.String(), nullable=True),
            sa.Column("notified", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        )


def downgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "user_reward_pins" in tables:
        op.drop_table("user_reward_pins")
    if "reward_configs" in tables:
        op.drop_table("reward_configs")
