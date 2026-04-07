"""
Usage limit checker for subscription enforcement.
Call check_usage_limit() before AI generate/publish endpoints.
"""
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.usage_log import UsageLog
from app.models.user import User


async def _get_subscription(user: User, db: AsyncSession) -> Subscription | None:
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    return result.scalar_one_or_none()


async def _count_usage_this_month(user_id, action_type: str, db: AsyncSession) -> int:
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    result = await db.execute(
        select(func.count()).where(
            UsageLog.user_id == user_id,
            UsageLog.action_type == action_type,
            UsageLog.billing_period == period,
        )
    )
    return result.scalar() or 0


async def check_usage_limit(user: User, action_type: str, db: AsyncSession) -> None:
    """
    Verify the user is allowed to perform action_type.
    Raises HTTPException(402/403/429) if not allowed.
    Logs the usage if allowed.

    During active trial: all features are unlocked, no response limits.
    After trial expires OR on paid plan: enforce plan limits and features.
    """
    sub = await _get_subscription(user, db)

    # No subscription → needs upgrade
    if sub is None:
        raise HTTPException(
            status_code=402,
            detail={"error": "no_subscription", "upgrade_url": "/dashboard/billing"},
        )

    # Check subscription status
    if sub.status not in ("active", "trialing"):
        raise HTTPException(
            status_code=402,
            detail={"error": "subscription_required", "upgrade_url": "/dashboard/billing"},
        )

    now = datetime.now(timezone.utc)

    # Trial expiry
    if sub.status == "trialing" and (not sub.trial_end or now > sub.trial_end):
        raise HTTPException(
            status_code=402,
            detail={"error": "trial_expired", "upgrade_url": "/dashboard/billing"},
        )

    # Active trial → ALL features unlocked, no usage limits
    if sub.status == "trialing":
        log = UsageLog(
            user_id=user.id,
            action_type=action_type,
            billing_period=now.strftime("%Y-%m"),
        )
        db.add(log)
        await db.flush()
        return

    # Manually set expiry on active subscription
    now = datetime.now(timezone.utc)
    if sub.status == "active" and sub.current_period_end and sub.current_period_end < now:
        raise HTTPException(
            status_code=402,
            detail={"error": "subscription_expired", "upgrade_url": "/dashboard/billing"},
        )

    # Paid subscription — get plan
    plan_result = await db.execute(select(Plan).where(Plan.id == sub.plan_id))
    plan = plan_result.scalar_one_or_none()

    if plan is None:
        return

    # Monthly response limit: admin override takes precedence over plan default.
    # None = unlimited; -1 override = unlimited; 0 plan default = unlimited.
    override = sub.responses_limit_override
    if override is not None:
        effective_limit = None if override == -1 else override
    else:
        plan_default = plan.max_responses_per_month
        effective_limit = None if plan_default == 0 else plan_default

    if effective_limit is not None and action_type in ("ai_generate", "ai_publish"):
        used = await _count_usage_this_month(user.id, action_type, db)
        if used >= effective_limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "monthly_limit_reached",
                    "used": used,
                    "limit": effective_limit,
                    "upgrade_url": "/dashboard/billing",
                },
            )

    # Feature gate
    if action_type == "auto_respond" and not plan.features.get("auto_respond"):
        raise HTTPException(
            status_code=403,
            detail={"error": "feature_not_available", "feature": "auto_respond", "upgrade_url": "/dashboard/billing"},
        )

    if action_type == "analytics" and not plan.features.get("analytics"):
        raise HTTPException(
            status_code=403,
            detail={"error": "feature_not_available", "feature": "analytics", "upgrade_url": "/dashboard/billing"},
        )

    if action_type == "export_csv" and not plan.features.get("export_csv"):
        raise HTTPException(
            status_code=403,
            detail={"error": "feature_not_available", "feature": "export_csv", "upgrade_url": "/dashboard/billing"},
        )

    # Log the usage
    log = UsageLog(
        user_id=user.id,
        action_type=action_type,
        billing_period=now.strftime("%Y-%m"),
    )
    db.add(log)
    await db.flush()


async def get_user_plan_features(user: User, db: AsyncSession) -> dict:
    """Returns plan features dict for the current user. Empty dict if no subscription."""
    sub = await _get_subscription(user, db)
    if sub is None:
        return {}
    plan_result = await db.execute(select(Plan).where(Plan.id == sub.plan_id))
    plan = plan_result.scalar_one_or_none()
    return plan.features if plan else {}
