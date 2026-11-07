from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c4e5f6a7b8c9"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("dragon_reservations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("revoked_at", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("source", sa.String(), server_default="", nullable=False))
        batch_op.add_column(sa.Column("external_reward_id", sa.String(), nullable=True))
        batch_op.create_index("uq_dragon_reservations_external_reward", ["external_reward_id"], unique=True)
    with op.batch_alter_table("user_reward_pins", schema=None) as batch_op:
        batch_op.add_column(sa.Column("source", sa.String(), server_default="", nullable=False))
        batch_op.add_column(sa.Column("external_reward_id", sa.String(), nullable=True))
        batch_op.create_index("uq_user_reward_pins_external_reward", ["external_reward_id"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("user_reward_pins", schema=None) as batch_op:
        batch_op.drop_index("uq_user_reward_pins_external_reward")
        batch_op.drop_column("external_reward_id")
        batch_op.drop_column("source")
    with op.batch_alter_table("dragon_reservations", schema=None) as batch_op:
        batch_op.drop_index("uq_dragon_reservations_external_reward")
        batch_op.drop_column("external_reward_id")
        batch_op.drop_column("source")
        batch_op.drop_column("revoked_at")
