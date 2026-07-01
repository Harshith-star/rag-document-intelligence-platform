"""add users.cache_version for AI answer cache key versioning

Revision ID: a862c5de59f2
Revises: 6b33ec96a820
Create Date: 2026-06-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "a862c5de59f2"
down_revision = "6b33ec96a820"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("cache_version", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("users", "cache_version")
