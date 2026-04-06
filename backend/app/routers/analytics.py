from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_plan_feature
from app.database import get_db
from app.models.location import Location
from app.models.response import Response
from app.models.review import Review

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("", dependencies=[Depends(require_plan_feature("analytics"))])
async def get_analytics(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return analytics summary for the current user's locations."""
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    loc_result = await db.execute(
        select(Location.id).where(
            Location.user_id == current_user.id,
            Location.is_active == True,  # noqa: E712
        )
    )
    location_ids = loc_result.scalars().all()

    if not location_ids:
        return {
            "total_reviews": 0,
            "reviews_last_30_days": 0,
            "reviews_last_7_days": 0,
            "average_rating": None,
            "response_rate": 0.0,
            "pending_reviews": 0,
            "rating_distribution": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
            "reviews_by_day": [],
        }

    total_result = await db.execute(
        select(func.count(Review.id)).where(Review.location_id.in_(location_ids))
    )
    total_reviews = total_result.scalar() or 0

    last30_result = await db.execute(
        select(func.count(Review.id)).where(
            Review.location_id.in_(location_ids),
            Review.review_date >= thirty_days_ago,
        )
    )
    reviews_last_30 = last30_result.scalar() or 0

    last7_result = await db.execute(
        select(func.count(Review.id)).where(
            Review.location_id.in_(location_ids),
            Review.review_date >= seven_days_ago,
        )
    )
    reviews_last_7 = last7_result.scalar() or 0

    avg_result = await db.execute(
        select(func.avg(Review.rating)).where(Review.location_id.in_(location_ids))
    )
    avg_rating = avg_result.scalar()
    average_rating = round(float(avg_rating), 2) if avg_rating else None

    pending_result = await db.execute(
        select(func.count(Review.id)).where(
            Review.location_id.in_(location_ids),
            Review.status == "pending",
        )
    )
    pending_reviews = pending_result.scalar() or 0

    responded_result = await db.execute(
        select(func.count(Response.id)).where(
            Response.review_id.in_(
                select(Review.id).where(Review.location_id.in_(location_ids))
            ),
            Response.published_at.isnot(None),
        )
    )
    responded_count = responded_result.scalar() or 0
    response_rate = round((responded_count / total_reviews * 100), 1) if total_reviews > 0 else 0.0

    dist_result = await db.execute(
        select(Review.rating, func.count(Review.id))
        .where(Review.location_id.in_(location_ids))
        .group_by(Review.rating)
    )
    rating_distribution = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    for rating, count in dist_result.all():
        rating_distribution[str(rating)] = count

    daily_result = await db.execute(
        select(
            func.date_trunc("day", Review.review_date).label("day"),
            func.count(Review.id).label("count"),
        )
        .where(
            Review.location_id.in_(location_ids),
            Review.review_date >= thirty_days_ago,
        )
        .group_by("day")
        .order_by("day")
    )
    reviews_by_day = [
        {"date": row.day.strftime("%Y-%m-%d"), "count": row.count}
        for row in daily_result.all()
    ]

    return {
        "total_reviews": total_reviews,
        "reviews_last_30_days": reviews_last_30,
        "reviews_last_7_days": reviews_last_7,
        "average_rating": average_rating,
        "response_rate": response_rate,
        "pending_reviews": pending_reviews,
        "rating_distribution": rating_distribution,
        "reviews_by_day": reviews_by_day,
    }
