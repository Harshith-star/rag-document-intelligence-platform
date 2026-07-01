"""Add query_logs.was_cached for cache hit analytics

Revision ID: b391dc47e101
Revises: a862c5de59f2
Create Date: 2026-07-01
"""
from alembic import op
import sqlalchemy as sa

revision      = "b391dc47e101"
down_revision = "a862c5de59f2"
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column(
        "query_logs",
        sa.Column("was_cached", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("query_logs", "was_cached")
