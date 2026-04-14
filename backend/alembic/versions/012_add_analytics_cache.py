"""add analytics_cache table

Revision ID: 012
Revises: 011
Create Date: 2026-04-14
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = inspector.get_table_names()

    if "analytics_cache" not in existing:
        op.create_table(
            "analytics_cache",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("period", sa.String(10), nullable=False),
            sa.Column("cache_date", sa.Date, nullable=False),
            sa.Column("result", postgresql.JSONB, nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "ix_analytics_cache_lookup",
            "analytics_cache",
            ["user_id", "location_id", "period", "cache_date"],
        )


def downgrade() -> None:
    op.drop_index("ix_analytics_cache_lookup", "analytics_cache")
    op.drop_table("analytics_cache")
