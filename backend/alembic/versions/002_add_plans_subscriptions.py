"""add plans and subscriptions

Revision ID: 002
Revises: 001
Create Date: 2026-03-15
"""
from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PLANS = [
    {
        "id": "starter",
        "name": "Starter",
        "stripe_price_id": "",
        "price_eur": 29,
        "max_locations": 1,
        "max_responses_per_month": 50,
        "features": json.dumps({
            "auto_respond": False,
            "telegram": True,
            "analytics": False,
            "export_csv": False,
            "white_label": False,
            "priority_support": False,
        }),
    },
    {
        "id": "pro",
        "name": "Pro",
        "stripe_price_id": "",
        "price_eur": 59,
        "max_locations": 3,
        "max_responses_per_month": 200,
        "features": json.dumps({
            "auto_respond": True,
            "telegram": True,
            "analytics": True,
            "export_csv": True,
            "white_label": False,
            "priority_support": False,
        }),
    },
    {
        "id": "agency",
        "name": "Agency",
        "stripe_price_id": "",
        "price_eur": 149,
        "max_locations": 10,
        "max_responses_per_month": 0,
        "features": json.dumps({
            "auto_respond": True,
            "telegram": True,
            "analytics": True,
            "export_csv": True,
            "white_label": True,
            "priority_support": True,
        }),
    },
]


def upgrade() -> None:
    # Plans table
    op.create_table(
        "plans",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("stripe_price_id", sa.String(100), server_default=""),
        sa.Column("price_eur", sa.Integer, nullable=False),
        sa.Column("max_locations", sa.Integer, nullable=False),
        sa.Column("max_responses_per_month", sa.Integer, nullable=False),
        sa.Column("features", postgresql.JSONB, server_default="{}"),
    )

    # Seed plans
    op.bulk_insert(
        sa.table(
            "plans",
            sa.column("id", sa.String),
            sa.column("name", sa.String),
            sa.column("stripe_price_id", sa.String),
            sa.column("price_eur", sa.Integer),
            sa.column("max_locations", sa.Integer),
            sa.column("max_responses_per_month", sa.Integer),
            sa.column("features", sa.Text),
        ),
        PLANS,
    )

    # Subscriptions table
    op.create_table(
        "subscriptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "plan_id",
            sa.String(50),
            sa.ForeignKey("plans.id"),
            nullable=False,
            server_default="starter",
        ),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="trialing"),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_subscriptions_stripe_sub_id", "subscriptions", ["stripe_subscription_id"])


def downgrade() -> None:
    op.drop_table("subscriptions")
    op.drop_table("plans")
