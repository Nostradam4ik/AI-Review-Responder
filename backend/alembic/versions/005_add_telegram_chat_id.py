"""add telegram_chat_id to users

Revision ID: 005
Revises: 004
Create Date: 2026-03-24
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("telegram_chat_id", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "telegram_chat_id")
