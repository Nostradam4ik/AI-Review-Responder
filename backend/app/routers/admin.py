"""Admin-only endpoints for managing users and monitoring the business."""
import uuid
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.location import Location
from app.models.plan import Plan
from app.models.response import Response
from app.models.review import Review
from app.models.subscription import Subscription
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ---------------------------------------------------------------------------
# GET /admin/stats
# ---------------------------------------------------------------------------

@router.get("/stats")
async def get_stats(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    total_users = (
        await db.execute(select(func.count(User.id)).where(User.is_active == True))  # noqa: E712
    ).scalar() or 0

    active_subs = (
        await db.execute(
            select(func.count(Subscription.id)).where(Subscription.status == "active")
        )
    ).scalar() or 0

    trial_users = (
        await db.execute(
            select(func.count(Subscription.id)).where(
                Subscription.status == "trialing",
                Subscription.trial_end > now,
            )
        )
    ).scalar() or 0

    expired_trials = (
        await db.execute(
            select(func.count(Subscription.id)).where(
                Subscription.status == "trialing",
                Subscription.trial_end <= now,
            )
        )
    ).scalar() or 0

    # MRR: sum plan prices for active subscriptions
    mrr_result = await db.execute(
        select(func.sum(Plan.price_eur))
        .join(Subscription, Subscription.plan_id == Plan.id)
        .where(Subscription.status == "active")
    )
    mrr = float(mrr_result.scalar() or 0)

    new_today = (
        await db.execute(
            select(func.count(User.id)).where(User.created_at >= today_start)
        )
    ).scalar() or 0

    new_this_week = (
        await db.execute(
            select(func.count(User.id)).where(User.created_at >= week_ago)
        )
    ).scalar() or 0

    return {
        "total_users": total_users,
        "active_subscriptions": active_subs,
        "trial_users": trial_users,
        "expired_trials": expired_trials,
        "mrr": mrr,
        "new_users_today": new_today,
        "new_users_this_week": new_this_week,
    }


# ---------------------------------------------------------------------------
# GET /admin/users
# ---------------------------------------------------------------------------

@router.get("/users")
async def list_users(
    search: str | None = Query(None),
    status: str = Query("all"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    offset = (page - 1) * limit

    # Correlated subqueries for counts
    loc_count_sq = (
        select(func.count(Location.id))
        .where(Location.user_id == User.id, Location.is_active == True)  # noqa: E712
        .correlate(User)
        .scalar_subquery()
    )
    rev_count_sq = (
        select(func.count(Review.id))
        .join(Location, Location.id == Review.location_id)
        .where(Location.user_id == User.id)
        .correlate(User)
        .scalar_subquery()
    )
    resp_count_sq = (
        select(func.count(Response.id))
        .join(Review, Review.id == Response.review_id)
        .join(Location, Location.id == Review.location_id)
        .where(Location.user_id == User.id)
        .correlate(User)
        .scalar_subquery()
    )

    # Build filter conditions
    conditions = [User.is_active == True]  # noqa: E712
    if search:
        ilike = f"%{search}%"
        conditions.append(
            or_(User.email.ilike(ilike), User.business_name.ilike(ilike))
        )
    if status == "trial":
        conditions.extend([
            Subscription.status == "trialing",
            Subscription.trial_end > now,
        ])
    elif status == "active":
        conditions.append(Subscription.status == "active")
    elif status == "expired":
        conditions.extend([
            Subscription.status == "trialing",
            Subscription.trial_end <= now,
        ])
    elif status == "cancelled":
        conditions.append(Subscription.status.in_(["cancelled", "past_due"]))

    join_needed = status in ("trial", "active", "expired", "cancelled")

    # Count query
    count_stmt = select(func.count(User.id))
    if join_needed:
        count_stmt = count_stmt.join(Subscription, Subscription.user_id == User.id)
    else:
        count_stmt = count_stmt.outerjoin(Subscription, Subscription.user_id == User.id)
    count_stmt = count_stmt.where(*conditions)
    total = (await db.execute(count_stmt)).scalar() or 0

    # Data query
    data_stmt = (
        select(
            User,
            Subscription,
            loc_count_sq.label("locations_count"),
            rev_count_sq.label("reviews_count"),
            resp_count_sq.label("responses_count"),
        )
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if join_needed:
        data_stmt = data_stmt.join(Subscription, Subscription.user_id == User.id)
    else:
        data_stmt = data_stmt.outerjoin(Subscription, Subscription.user_id == User.id)
    data_stmt = data_stmt.where(*conditions)

    rows = (await db.execute(data_stmt)).all()

    users_out = []
    for row in rows:
        u: User = row.User
        sub: Subscription | None = row.Subscription

        is_trial = bool(
            sub
            and sub.status == "trialing"
            and sub.trial_end
            and sub.trial_end > now
        )
        trial_days_remaining: int | None = None
        if is_trial and sub and sub.trial_end:
            trial_days_remaining = max(0, (sub.trial_end - now).days)

        users_out.append({
            "id": str(u.id),
            "email": u.email,
            "name": u.business_name,
            "avatar_url": None,
            "plan_name": (sub.plan_id.capitalize() if sub else "Free"),
            "subscription_status": (sub.status if sub else "none"),
            "is_trial": is_trial,
            "trial_days_remaining": trial_days_remaining,
            "created_at": u.created_at.isoformat(),
            "last_seen_at": None,
            "locations_count": row.locations_count or 0,
            "reviews_count": row.reviews_count or 0,
            "responses_count": row.responses_count or 0,
            "is_admin": u.is_admin,
        })

    return {
        "users": users_out,
        "total": total,
        "page": page,
        "pages": max(1, -(-total // limit)),  # ceiling division
    }


# ---------------------------------------------------------------------------
# POST /admin/users/{user_id}/reset-trial
# ---------------------------------------------------------------------------

class ResetTrialBody(BaseModel):
    days: int = 14


@router.post("/users/{user_id}/reset-trial")
async def reset_trial(
    user_id: str,
    body: ResetTrialBody,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(400, "Invalid user_id")

    result = await db.execute(
        select(Subscription).where(Subscription.user_id == uid)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(404, "Subscription not found")

    sub.status = "trialing"
    sub.trial_end = datetime.now(timezone.utc) + timedelta(days=body.days)
    sub.stripe_subscription_id = None

    user = await db.get(User, uid)
    if user:
        user.plan = sub.plan_id

    await db.commit()
    logger.info("Admin reset trial for user %s — %d days", user_id, body.days)
    return {"reset": True, "trial_end": sub.trial_end.isoformat()}


# ---------------------------------------------------------------------------
# POST /admin/users/{user_id}/change-plan
# ---------------------------------------------------------------------------

class ChangePlanBody(BaseModel):
    plan: str
    reason: str = ""


@router.post("/users/{user_id}/change-plan")
async def change_plan(
    user_id: str,
    body: ChangePlanBody,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    valid_plans = ("starter", "pro", "agency")
    if body.plan not in valid_plans:
        raise HTTPException(400, f"plan must be one of {valid_plans}")

    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(400, "Invalid user_id")

    plan_result = await db.execute(select(Plan).where(Plan.id == body.plan))
    if plan_result.scalar_one_or_none() is None:
        raise HTTPException(400, "Plan not found in database")

    result = await db.execute(
        select(Subscription).where(Subscription.user_id == uid)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(404, "Subscription not found")

    sub.plan_id = body.plan
    sub.status = "active"
    sub.trial_end = None

    user = await db.get(User, uid)
    if user:
        user.plan = body.plan

    await db.commit()
    logger.info(
        "Admin changed plan for user %s → %s (reason: %s)",
        user_id, body.plan, body.reason,
    )
    return {"changed": True, "plan": body.plan}


# ---------------------------------------------------------------------------
# DELETE /admin/users/{user_id}  — soft delete
# ---------------------------------------------------------------------------

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(400, "Invalid user_id")

    user = await db.get(User, uid)
    if not user:
        raise HTTPException(404, "User not found")
    if user.is_admin:
        raise HTTPException(403, "Cannot delete an admin account")

    user.is_active = False
    user.email = f"deleted_{user.id}@deleted.com"
    user.google_id = None
    user.password_hash = None
    user.access_token = None
    user.refresh_token = None
    user.telegram_chat_id = None

    await db.commit()
    logger.info("Admin soft-deleted user %s", user_id)
    return {"deleted": True}
