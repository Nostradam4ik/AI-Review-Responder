"""add refresh_token_jti to users

Revision ID: 015
Revises: 014
Create Date: 2026-04-20
"""
import sqlalchemy as sa
from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("refresh_token_jti", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "refresh_token_jti")
