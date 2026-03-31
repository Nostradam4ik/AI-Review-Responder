"""update plan prices and response limits

Revision ID: 007
Revises: 006
Create Date: 2026-03-31
"""
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE plans SET price_eur=19, max_responses_per_month=100 WHERE id='starter'")
    op.execute("UPDATE plans SET price_eur=39, max_responses_per_month=0 WHERE id='pro'")
    op.execute("UPDATE plans SET price_eur=79 WHERE id='agency'")


def downgrade() -> None:
    op.execute("UPDATE plans SET price_eur=29, max_responses_per_month=50 WHERE id='starter'")
    op.execute("UPDATE plans SET price_eur=59, max_responses_per_month=200 WHERE id='pro'")
    op.execute("UPDATE plans SET price_eur=149 WHERE id='agency'")
