"""init

Revision ID: 0001_init
Revises: 
Create Date: 2025-10-17 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "url_map",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=12), nullable=False, unique=True),
        sa.Column("target", sa.String(length=2048), nullable=False),
    )
    op.create_index(op.f("ix_url_map_code"), "url_map", ["code"], unique=False)

    op.create_table(
        "visit",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("url_id", sa.Integer(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=False),
        sa.Column("ua", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("ref", sa.String(length=512), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["url_id"], ["url_map.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("visit")
    op.drop_index(op.f("ix_url_map_code"), table_name="url_map")
    op.drop_table("url_map")

