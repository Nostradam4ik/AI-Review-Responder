#!/usr/bin/env python3
"""Grant admin access to a user by email.

Usage (from backend/ directory):
    python scripts/make_admin.py user@example.com
"""
import asyncio
import sys
from pathlib import Path

# Ensure the backend package is importable when run from the backend/ dir
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select  # noqa: E402

from app.database import async_session  # noqa: E402
from app.models.user import User  # noqa: E402


async def make_admin(email: str) -> None:
    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            print(f"Error: no user found with email '{email}'")
            sys.exit(1)

        if user.is_admin:
            print(f"'{email}' is already an admin — no change made.")
            return

        user.is_admin = True
        await db.commit()
        print(f"Done: '{email}' is now an admin.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/make_admin.py <email>")
        sys.exit(1)

    asyncio.run(make_admin(sys.argv[1]))
