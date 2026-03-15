"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("business_name", sa.String(255), nullable=True),
        sa.Column("google_id", sa.String(255), unique=True, nullable=True),
        sa.Column("access_token", sa.Text, nullable=True),
        sa.Column("refresh_token", sa.Text, nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tone_preference", sa.String(20), server_default="warm"),
        sa.Column("language", sa.String(10), server_default="auto"),
        sa.Column("plan", sa.String(20), server_default="free"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # Locations
    op.create_table(
        "locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gmb_location_id", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
    )

    # Reviews
    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gmb_review_id", sa.String(255), unique=True, nullable=False),
        sa.Column("author_name", sa.String(255), nullable=True),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("review_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating"),
    )

    # Responses
    op.create_table(
        "responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("review_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ai_draft", sa.Text, nullable=False),
        sa.Column("final_text", sa.Text, nullable=True),
        sa.Column("tone_used", sa.String(20), nullable=True),
        sa.Column("model_used", sa.String(50), nullable=True),
        sa.Column("was_edited", sa.Boolean, server_default=sa.text("false")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("responses")
    op.drop_table("reviews")
    op.drop_table("locations")
    op.drop_table("users")
