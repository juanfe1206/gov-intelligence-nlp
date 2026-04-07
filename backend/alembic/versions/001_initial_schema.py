"""Initial schema - raw_posts and processed_posts tables

Revision ID: 001
Revises:
Create Date: 2026-04-07

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    # NOTE: pgvector extension must be installed on PostgreSQL
    # Install with: CREATE EXTENSION vector;
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')

    # Create raw_posts table
    op.create_table(
        "raw_posts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=100), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create processed_posts table
    op.create_table(
        "processed_posts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("raw_post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column("subtopic", sa.String(length=100), nullable=True),
        sa.Column("sentiment", sa.String(length=20), nullable=False),
        sa.Column("target", sa.String(length=255), nullable=True),
        sa.Column("intensity", sa.Float(), nullable=True),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("model_version", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(
            ["raw_post_id"],
            ["raw_posts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create index for faster lookups
    op.create_index("ix_processed_posts_raw_post_id", "processed_posts", ["raw_post_id"])


def downgrade() -> None:
    op.drop_index("ix_processed_posts_raw_post_id", table_name="processed_posts")
    op.drop_table("processed_posts")
    op.drop_table("raw_posts")
