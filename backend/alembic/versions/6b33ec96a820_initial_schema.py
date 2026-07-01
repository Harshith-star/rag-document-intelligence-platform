"""initial schema: users, documents, query_logs

Revision ID: 6b33ec96a820
Revises:
Create Date: 2026-06-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "6b33ec96a820"
down_revision = None
branch_labels = None
depends_on = None

processing_status_enum = sa.Enum(
    "pending", "processing", "completed", "failed", name="processingstatus"
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("email", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("filename", sa.String(), nullable=False, index=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("file_size", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("file_type", sa.String(), nullable=True, server_default=""),
        sa.Column("num_chunks", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("processing_status", processing_status_enum, nullable=True, server_default="pending"),
        sa.Column("processing_time", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "query_logs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True),
        sa.Column("question", sa.String(), nullable=False),
        sa.Column("response_time", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("query_logs")
    op.drop_table("documents")
    op.drop_table("users")
    processing_status_enum.drop(op.get_bind(), checkfirst=True)
