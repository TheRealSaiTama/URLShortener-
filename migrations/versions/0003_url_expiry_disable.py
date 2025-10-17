"""url expiry + disable

Revision ID: 0003_url_expiry_disable
Revises: 0002_visit_indexes
Create Date: 2025-10-17 00:10:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_url_expiry_disable"
down_revision = "0002_visit_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("url_map", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "url_map",
        sa.Column("disabled", sa.Boolean(), server_default=sa.text("0"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("url_map", "disabled")
    op.drop_column("url_map", "expires_at")

