"""abuse protection: was_cache_hit column, plan response limits

Revision ID: 013
Revises: 012
Create Date: 2026-04-14
"""
import sqlalchemy as sa
from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add was_cache_hit column to analytics_cache
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("analytics_cache")]

    if "was_cache_hit" not in columns:
        op.add_column(
            "analytics_cache",
            sa.Column("was_cache_hit", sa.Boolean, nullable=False, server_default="false"),
        )
    if "created_at" not in columns:
        op.add_column(
            "analytics_cache",
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

    # Fix plan response limits: Pro=500, Agency=2000
    op.execute("UPDATE plans SET max_responses_per_month = 500 WHERE id = 'pro' AND max_responses_per_month = 0")
    op.execute("UPDATE plans SET max_responses_per_month = 2000 WHERE id = 'agency' AND max_responses_per_month = 0")


def downgrade() -> None:
    op.drop_column("analytics_cache", "created_at")
    op.drop_column("analytics_cache", "was_cache_hit")
    op.execute("UPDATE plans SET max_responses_per_month = 0 WHERE id IN ('pro', 'agency')")
