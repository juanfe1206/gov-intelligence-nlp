"""Add ingestion_jobs table and content_hash for deduplication

Revision ID: 002
Revises: 001
Create Date: 2026-04-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add content_hash column to raw_posts
    op.add_column(
        "raw_posts",
        sa.Column("content_hash", sa.String(length=64), nullable=True),
    )

    # Create unique index for deduplication (source + content_hash)
    op.create_index(
        "ix_raw_posts_source_content_hash",
        "raw_posts",
        ["source", "content_hash"],
        unique=True,
        postgresql_where=sa.text("content_hash IS NOT NULL"),
    )

    # Create ingestion_jobs table
    op.create_table(
        "ingestion_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("inserted_count", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("skipped_count", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("duplicate_count", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column(
            "error_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create index on ingestion_jobs for status queries
    op.create_index(
        "ix_ingestion_jobs_source_started_at",
        "ingestion_jobs",
        ["source", "started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ingestion_jobs_source_started_at", table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")
    op.drop_index("ix_raw_posts_source_content_hash", table_name="raw_posts")
    op.drop_column("raw_posts", "content_hash")
