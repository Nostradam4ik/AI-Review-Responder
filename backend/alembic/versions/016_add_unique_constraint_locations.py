"""add unique constraint user_id google_location_id on locations

Revision ID: 016
Revises: 015
Create Date: 2026-04-22

"""
from typing import Sequence, Union

from alembic import op

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_locations_user_google",
        "locations",
        ["user_id", "gmb_location_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_locations_user_google", "locations")
