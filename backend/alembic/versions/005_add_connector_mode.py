"""Add connector mode column to ingestion_jobs

Revision ID: 005
Revises: 004
Create Date: 2026-04-09

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Add mode column to ingestion_jobs to distinguish between live and replay runs
    if not _has_column(inspector, "ingestion_jobs", "mode"):
        op.add_column(
            "ingestion_jobs",
            sa.Column("mode", sa.String(length=10), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_column(inspector, "ingestion_jobs", "mode"):
        op.drop_column("ingestion_jobs", "mode")
