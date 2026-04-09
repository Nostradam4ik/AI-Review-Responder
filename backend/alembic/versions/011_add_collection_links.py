"""add review_collection_links and internal_feedback tables

Revision ID: 011
Revises: 010
Create Date: 2026-04-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_collection_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("location_id", UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.String(64), unique=True, nullable=False),
        sa.Column("google_maps_url", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_review_collection_links_slug", "review_collection_links", ["slug"])

    op.create_table(
        "internal_feedback",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("link_id", UUID(as_uuid=True), sa.ForeignKey("review_collection_links.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("comment", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("internal_feedback")
    op.drop_index("ix_review_collection_links_slug", "review_collection_links")
    op.drop_table("review_collection_links")
