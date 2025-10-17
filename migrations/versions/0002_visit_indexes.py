"""visit indexes

Revision ID: 0002_visit_indexes
Revises: 0001_init
Create Date: 2025-10-17 00:05:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_visit_indexes"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # For Postgres: descending index on ts
    op.create_index("ix_visit_url_ts", "visit", [sa.text("url_id"), sa.text("ts DESC")])


def downgrade() -> None:
    op.drop_index("ix_visit_url_ts", table_name="visit")

