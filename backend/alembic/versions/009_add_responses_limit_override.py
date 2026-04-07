"""add responses_limit_override to subscriptions

Revision ID: 009
Revises: 008
Create Date: 2026-04-07
"""
from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("responses_limit_override", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "responses_limit_override")
