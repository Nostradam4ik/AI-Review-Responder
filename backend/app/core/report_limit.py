"""Daily cap on Intelligence Report LLM calls per user per plan."""
from datetime import date

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics_cache import AnalyticsCache
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User

DAILY_REPORT_LIMITS: dict[str, int] = {
    "starter": 0,  # analytics not available on starter
    "pro": 4,      # 4 real LLM calls/day (6h cache = natural limit)
    "agency": 8,   # 8 real LLM calls/day
}


async def _get_user_plan_name(user: User, db: AsyncSession) -> str:
    """Return the user's current plan id (e.g. 'starter', 'pro', 'agency')."""
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        return "free"

    plan_result = await db.execute(select(Plan).where(Plan.id == sub.plan_id))
    plan = plan_result.scalar_one_or_none()
    return plan.id if plan else "free"


async def check_report_daily_limit(user: User, db: AsyncSession) -> None:
    """
    Count real LLM Intelligence Report calls made by this user today.
    Raises HTTPException(403) if feature unavailable, HTTPException(429) if over cap.
    Cache hits (was_cache_hit=True) do not count against the limit.
    """
    today = date.today()

    result = await db.execute(
        select(func.count()).where(
            AnalyticsCache.user_id == user.id,
            AnalyticsCache.cache_date == today,
            AnalyticsCache.was_cache_hit == False,  # noqa: E712
        )
    )
    count = result.scalar() or 0

    plan_name = await _get_user_plan_name(user, db)
    limit = DAILY_REPORT_LIMITS.get(plan_name, 0)

    if limit == 0:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "feature_not_available",
                "feature": "analytics",
                "upgrade_url": "/dashboard/billing",
            },
        )

    if count >= limit:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "daily_report_limit_reached",
                "used": count,
                "limit": limit,
                "resets_at": "midnight UTC",
                "message": (
                    f"You've generated {count}/{limit} reports today. "
                    "Cached reports are free — wait for cache refresh or upgrade your plan."
                ),
            },
        )
