"""Add connector support: external_id column, partial unique index, and connector_checkpoints table

Revision ID: 004
Revises: 003
Create Date: 2026-04-09

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _has_index(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Add external_id column to raw_posts (nullable for backward compatibility with CSV rows)
    if not _has_column(inspector, "raw_posts", "external_id"):
        op.add_column(
            "raw_posts",
            sa.Column("external_id", sa.String(length=255), nullable=True),
        )

    # Create partial unique index for platform + external_id (only where external_id IS NOT NULL)
    # This prevents duplicate connector posts without affecting CSV-ingested rows
    if not _has_index(inspector, "raw_posts", "uq_raw_posts_platform_external_id"):
        op.create_index(
            "uq_raw_posts_platform_external_id",
            "raw_posts",
            ["platform", "external_id"],
            unique=True,
            postgresql_where=sa.text("external_id IS NOT NULL"),
        )

    # Create connector_checkpoints table
    if not _has_table(inspector, "connector_checkpoints"):
        op.create_table(
            "connector_checkpoints",
            sa.Column("connector_id", sa.String(length=255), nullable=False),
            sa.Column("checkpoint_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("connector_id"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Drop connector_checkpoints table
    if _has_table(inspector, "connector_checkpoints"):
        op.drop_table("connector_checkpoints")

    # Drop partial unique index
    if _has_index(inspector, "raw_posts", "uq_raw_posts_platform_external_id"):
        op.drop_index("uq_raw_posts_platform_external_id", table_name="raw_posts")

    # Drop external_id column
    if _has_column(inspector, "raw_posts", "external_id"):
        op.drop_column("raw_posts", "external_id")
