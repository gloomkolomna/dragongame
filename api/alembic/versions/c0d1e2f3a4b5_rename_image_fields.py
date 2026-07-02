"""rename image fields: image_path->egg_path, silhouette_path->dragon_path

Revision ID: c0d1e2f3a4b5
Revises: a1b2c3d4e5f6
Create Date: 2026-07-02 21:00:00.000000

Семантика колонок была контринтуитивной: image_path хранил ЯЙЦО,
а silhouette_path — ВЗРОСЛОГО ДРАКОНА. Переименовываем так, чтобы
имена соответствовали содержимому. Сами значения (пути к файлам)
и физические файлы на диске не меняются.
"""
from typing import Sequence, Union
from alembic import op


revision: str = 'c0d1e2f3a4b5'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('dragons', schema=None) as batch_op:
        batch_op.alter_column('image_path', new_column_name='egg_path')
        batch_op.alter_column('silhouette_path', new_column_name='dragon_path')


def downgrade() -> None:
    with op.batch_alter_table('dragons', schema=None) as batch_op:
        batch_op.alter_column('egg_path', new_column_name='image_path')
        batch_op.alter_column('dragon_path', new_column_name='silhouette_path')
