"""add donor_cache.first_don_since with backfill

Revision ID: v1d2o3n4c5a6
Revises: s2t3u4v5w6x7
Create Date: 2026-08-17 20:00:00.000000

first_don_since — самая ранняя известная дата доната (не сдвигается
при продлениях подписки). Бэкфилл: минимум из don_since, первого
события donut_subscription_create и даты первого бесплатного яйца
(выдача доказывает, что игрок уже был доном).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'v1d2o3n4c5a6'
down_revision: Union[str, None] = 's2t3u4v5w6x7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('donor_cache', schema=None) as batch_op:
        batch_op.add_column(sa.Column('first_don_since', sa.String(), nullable=True))

    op.execute(
        "UPDATE donor_cache SET first_don_since = don_since "
        "WHERE first_don_since IS NULL AND don_since IS NOT NULL AND don_since != ''"
    )
    op.execute(
        "UPDATE donor_cache SET first_don_since = ("
        "  SELECT MIN(e.created_at) FROM donor_event_logs e"
        "  WHERE e.vk_id = donor_cache.vk_id AND e.event_type = 'donut_subscription_create'"
        ") WHERE first_don_since IS NULL OR first_don_since > ("
        "  SELECT MIN(e.created_at) FROM donor_event_logs e"
        "  WHERE e.vk_id = donor_cache.vk_id AND e.event_type = 'donut_subscription_create'"
        ")"
    )
    op.execute(
        "UPDATE donor_cache SET first_don_since = ("
        "  SELECT MIN(p.issued_at) FROM user_reward_pins p"
        "  WHERE p.user_id = donor_cache.vk_id AND p.config_id IS NOT NULL"
        ") WHERE first_don_since IS NULL OR first_don_since > ("
        "  SELECT MIN(p.issued_at) FROM user_reward_pins p"
        "  WHERE p.user_id = donor_cache.vk_id AND p.config_id IS NOT NULL"
        ")"
    )


def downgrade() -> None:
    with op.batch_alter_table('donor_cache', schema=None) as batch_op:
        batch_op.drop_column('first_don_since')
