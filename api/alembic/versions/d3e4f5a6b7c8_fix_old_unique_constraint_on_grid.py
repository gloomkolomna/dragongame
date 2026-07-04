"""fix old unique constraint on collection_grid

Revision ID: d3e4f5a6b7c8
Revises: bf1b946df94e
Create Date: 2026-07-04 20:10:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, None] = 'bf1b946df94e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE _collection_grid_new (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            family_id INTEGER NOT NULL,
            cell_x INTEGER NOT NULL,
            cell_y INTEGER NOT NULL,
            dragon_id INTEGER,
            FOREIGN KEY (family_id) REFERENCES families (id) ON DELETE CASCADE,
            FOREIGN KEY (dragon_id) REFERENCES dragons (id) ON DELETE SET NULL,
            UNIQUE (family_id, cell_x, cell_y),
            UNIQUE (dragon_id)
        )
    """)
    op.execute("INSERT INTO _collection_grid_new SELECT id, family_id, cell_x, cell_y, dragon_id FROM collection_grid")
    op.execute("DROP TABLE collection_grid")
    op.execute("ALTER TABLE _collection_grid_new RENAME TO collection_grid")


def downgrade() -> None:
    op.execute("""
        CREATE TABLE _collection_grid_old (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            family_id INTEGER NOT NULL,
            cell_x INTEGER NOT NULL,
            cell_y INTEGER NOT NULL,
            dragon_id INTEGER,
            FOREIGN KEY (family_id) REFERENCES families (id) ON DELETE CASCADE,
            FOREIGN KEY (dragon_id) REFERENCES dragons (id) ON DELETE SET NULL,
            UNIQUE (family_id, cell_x, cell_y),
            UNIQUE (cell_x, cell_y),
            UNIQUE (dragon_id)
        )
    """)
    op.execute("INSERT INTO _collection_grid_old SELECT id, family_id, cell_x, cell_y, dragon_id FROM collection_grid")
    op.execute("DROP TABLE collection_grid")
    op.execute("ALTER TABLE _collection_grid_old RENAME TO collection_grid")
