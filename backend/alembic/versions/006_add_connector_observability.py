"""Add normalized_count and failure_category to ingestion_jobs

Revision ID: 006
Revises: 005
Create Date: 2026-04-09

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Add normalized_count column to track records passing normalization
    if not _has_column(inspector, "ingestion_jobs", "normalized_count"):
        op.add_column(
            "ingestion_jobs",
            sa.Column("normalized_count", sa.Integer(), nullable=True),
        )

    # Add failure_category column for machine-readable error categorization
    if not _has_column(inspector, "ingestion_jobs", "failure_category"):
        op.add_column(
            "ingestion_jobs",
            sa.Column("failure_category", sa.String(length=50), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_column(inspector, "ingestion_jobs", "failure_category"):
        op.drop_column("ingestion_jobs", "failure_category")
    if _has_column(inspector, "ingestion_jobs", "normalized_count"):
        op.drop_column("ingestion_jobs", "normalized_count")
