"""Add processing columns and job_type for NLP pipeline

Revision ID: 003
Revises: 002
Create Date: 2026-04-07

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def _count_non_null_embeddings(bind) -> int:
    return int(
        bind.execute(
            sa.text("SELECT COUNT(*) FROM processed_posts WHERE embedding IS NOT NULL")
        ).scalar_one()
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Add error tracking columns to processed_posts
    if not _has_column(inspector, "processed_posts", "error_status"):
        op.add_column(
            "processed_posts",
            sa.Column("error_status", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        )
    if not _has_column(inspector, "processed_posts", "error_message"):
        op.add_column(
            "processed_posts",
            sa.Column("error_message", sa.Text(), nullable=True),
        )

    # Add job_type column to ingestion_jobs to distinguish between ingest and process jobs
    if not _has_column(inspector, "ingestion_jobs", "job_type"):
        op.add_column(
            "ingestion_jobs",
            sa.Column("job_type", sa.String(length=50), nullable=True, server_default="ingest"),
        )

    # Create indexes used by processing queries
    if not _has_index(inspector, "ingestion_jobs", "ix_ingestion_jobs_job_type"):
        op.create_index(
            "ix_ingestion_jobs_job_type",
            "ingestion_jobs",
            ["job_type"],
        )

    if not _has_index(inspector, "processed_posts", "ix_processed_posts_error_status"):
        op.create_index(
            "ix_processed_posts_error_status",
            "processed_posts",
            ["error_status"],
        )

    # Supports NOT EXISTS query for unprocessed raw posts.
    if not _has_index(inspector, "processed_posts", "ix_processed_posts_raw_post_id"):
        op.create_index(
            "ix_processed_posts_raw_post_id",
            "processed_posts",
            ["raw_post_id"],
        )

    # Update vector dimension from 768 to 1536 for text-embedding-3-small.
    embedding_type = bind.execute(
        sa.text(
            """
            SELECT format_type(a.atttypid, a.atttypmod)
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relname = 'processed_posts'
              AND a.attname = 'embedding'
              AND a.attnum > 0
              AND NOT a.attisdropped
            """
        )
    ).scalar_one_or_none()
    if embedding_type == "vector(768)":
        existing_count = _count_non_null_embeddings(bind)
        if existing_count > 0:
            raise RuntimeError(
                "Cannot auto-migrate embeddings from vector(768) to vector(1536) with existing non-null values. "
                "Backfill embeddings to 1536 dimensions before rerunning this migration."
            )
        op.execute("ALTER TABLE processed_posts ALTER COLUMN embedding TYPE vector(1536)")


def downgrade() -> None:
    bind = op.get_bind()
    embedding_type = bind.execute(
        sa.text(
            """
            SELECT format_type(a.atttypid, a.atttypmod)
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relname = 'processed_posts'
              AND a.attname = 'embedding'
              AND a.attnum > 0
              AND NOT a.attisdropped
            """
        )
    ).scalar_one_or_none()

    if embedding_type == "vector(1536)":
        existing_count = _count_non_null_embeddings(bind)
        if existing_count > 0:
            raise RuntimeError(
                "Cannot auto-downgrade embeddings from vector(1536) to vector(768) with existing non-null values."
            )
        op.execute("ALTER TABLE processed_posts ALTER COLUMN embedding TYPE vector(768)")

    # Drop indexes
    op.drop_index("ix_processed_posts_error_status", table_name="processed_posts")
    op.drop_index("ix_ingestion_jobs_job_type", table_name="ingestion_jobs")
    op.drop_index("ix_processed_posts_raw_post_id", table_name="processed_posts")

    # Drop columns
    op.drop_column("processed_posts", "error_message")
    op.drop_column("processed_posts", "error_status")
    op.drop_column("ingestion_jobs", "job_type")
