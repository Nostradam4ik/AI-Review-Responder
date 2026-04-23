import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response as FastAPIResponse
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_plan_feature
from app.database import get_db
from app.models.analytics_cache import AnalyticsCache
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
        select(func.count(func.distinct(Response.review_id))).where(
            Response.review_id.in_(
                select(Review.id).where(Review.location_id.in_(location_ids))
            )
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


# ── Intelligence Report helpers ───────────────────────────────────────────────

def _period_dates(period: str) -> tuple[datetime, datetime, datetime, datetime]:
    """Return (current_start, current_end, prev_start, prev_end) for week/month."""
    now = datetime.now(timezone.utc)
    days = 7 if period == "week" else 30
    current_start = now - timedelta(days=days)
    prev_start = now - timedelta(days=days * 2)
    prev_end = current_start
    return current_start, now, prev_start, prev_end


def _period_label(period: str) -> str:
    now = datetime.now(timezone.utc)
    days = 7 if period == "week" else 30
    start = now - timedelta(days=days)
    return f"{start.strftime('%b %d')} – {now.strftime('%b %d, %Y')}"


async def _fetch_reviews(
    db: AsyncSession,
    location_ids: list,
    since: datetime,
    until: datetime,
    location_id_filter: uuid.UUID | None = None,
) -> list[Review]:
    query = (
        select(Review)
        .where(
            Review.location_id.in_(location_ids),
            Review.review_date >= since,
            Review.review_date <= until,
            Review.comment.isnot(None),
        )
        .order_by(Review.review_date.desc())
    )
    if location_id_filter:
        query = query.where(Review.location_id == location_id_filter)
    result = await db.execute(query)
    return list(result.scalars().all())


async def _get_cached_report(
    db: AsyncSession,
    user_id: uuid.UUID,
    location_id: uuid.UUID | None,
    period: str,
) -> dict | None:
    today = date.today()
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(AnalyticsCache).where(
            AnalyticsCache.user_id == user_id,
            AnalyticsCache.location_id == location_id,
            AnalyticsCache.period == period,
            AnalyticsCache.cache_date == today,
            AnalyticsCache.expires_at > now,
        )
    )
    entry = result.scalar_one_or_none()
    return entry.result if entry else None


async def _save_cached_report(
    db: AsyncSession,
    user_id: uuid.UUID,
    location_id: uuid.UUID | None,
    period: str,
    result: dict,
    was_cache_hit: bool = False,
) -> None:
    """Append a new cache entry. Old entries are kept to allow daily-limit counting."""
    now = datetime.now(timezone.utc)
    today = date.today()
    cache_entry = AnalyticsCache(
        user_id=user_id,
        location_id=location_id,
        period=period,
        cache_date=today,
        result=result,
        expires_at=now + timedelta(hours=6),
        was_cache_hit=was_cache_hit,
    )
    db.add(cache_entry)
    await db.flush()


async def _build_report(
    db: AsyncSession,
    current_user,
    location_id: uuid.UUID | None,
    period: str,
) -> tuple[dict, dict]:
    """Generate (or load from cache) the intelligence analysis + build meta dict."""
    from groq import AsyncGroq
    from app.config import settings
    from app.core.report_limit import check_report_daily_limit
    from app.services.review_intelligence import generate_intelligence_report

    # 1. Check cache first — cache hit skips daily limit and LLM call
    cached = await _get_cached_report(db, current_user.id, location_id, period)
    if cached:
        analysis = cached
    else:
        # 2. Cache miss — enforce daily cap before calling LLM
        await check_report_daily_limit(current_user, db)

        # Get all active location IDs for the user
        loc_result = await db.execute(
            select(Location).where(
                Location.user_id == current_user.id,
                Location.is_active == True,  # noqa: E712
            )
        )
        locations = {loc.id: loc for loc in loc_result.scalars().all()}

        if not locations:
            analysis = {
                "business_type": "other",
                "overall_sentiment": "neutral",
                "avg_rating": 0.0,
                "nps_estimate": 0,
                "summary": "No locations found. Add a Google Business location to generate a report.",
                "complaints": [],
                "praises": [],
                "urgent_alerts": [],
                "opportunities": [],
                "comparison": {"vs_previous_period": "N/A", "response_rate": "N/A"},
                "action_plan": [],
            }
        else:
            current_start, current_end, prev_start, prev_end = _period_dates(period)
            reviews = await _fetch_reviews(db, list(locations.keys()), current_start, current_end, location_id)
            prev_reviews = await _fetch_reviews(db, list(locations.keys()), prev_start, prev_end, location_id)

            if location_id and location_id in locations:
                location_name = locations[location_id].name
            elif len(locations) == 1:
                location_name = next(iter(locations.values())).name
            else:
                location_name = f"{len(locations)} locations"

            groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
            analysis = await generate_intelligence_report(
                reviews=reviews,
                period_label=_period_label(period),
                location_name=location_name,
                previous_period_reviews=prev_reviews,
                groq_client=groq_client,
            )

        # 3. Save with was_cache_hit=False (real LLM call)
        await _save_cached_report(db, current_user.id, location_id, period, analysis, was_cache_hit=False)
        await db.commit()

    # Build meta
    loc_result2 = await db.execute(
        select(Location).where(Location.user_id == current_user.id, Location.is_active == True)  # noqa: E712
    )
    locations2 = list(loc_result2.scalars().all())

    current_start, current_end, _, _ = _period_dates(period)
    all_loc_ids = [l.id for l in locations2]  # noqa: E741

    total_reviews = 0
    response_rate = 0
    if all_loc_ids:
        q = select(func.count(Review.id)).where(
            Review.location_id.in_(all_loc_ids),
            Review.review_date >= current_start,
        )
        if location_id:
            q = q.where(Review.location_id == location_id)
        total_reviews = (await db.execute(q)).scalar() or 0

        total_q = select(func.count(Review.id)).where(Review.location_id.in_(all_loc_ids))
        if location_id:
            total_q = total_q.where(Review.location_id == location_id)
        total_all = (await db.execute(total_q)).scalar() or 0

        inner_reviews_q = select(Review.id).where(Review.location_id.in_(all_loc_ids))
        if location_id:
            inner_reviews_q = inner_reviews_q.where(Review.location_id == location_id)
        resp_q = select(func.count(func.distinct(Response.review_id))).where(
            Response.review_id.in_(inner_reviews_q)
        )
        responded = (await db.execute(resp_q)).scalar() or 0
        response_rate = round(responded / total_all * 100, 1) if total_all > 0 else 0.0

    loc_name = ""
    if location_id:
        for l in locations2:  # noqa: E741
            if l.id == location_id:
                loc_name = l.name
                break
    elif len(locations2) == 1:
        loc_name = locations2[0].name

    meta = {
        "business_name": current_user.business_name or current_user.email,
        "location_name": loc_name,
        "period_label": _period_label(period),
        "total_reviews": total_reviews,
        "response_rate": response_rate,
        "generated_at": datetime.now(timezone.utc).strftime("%B %d, %Y"),
    }

    return analysis, meta


# ── Report endpoints ──────────────────────────────────────────────────────────

@router.get("/report/preview", dependencies=[Depends(require_plan_feature("analytics"))])
async def preview_intelligence_report(
    location_id: uuid.UUID | None = Query(None),
    period: Literal["week", "month"] = Query("month"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the intelligence analysis as JSON for frontend rendering. PRO+ only."""
    analysis, meta = await _build_report(db, current_user, location_id, period)
    return JSONResponse({"analysis": analysis, "meta": meta})


@router.get("/report/download", dependencies=[Depends(require_plan_feature("analytics"))])
async def download_intelligence_report(
    location_id: uuid.UUID | None = Query(None),
    period: Literal["week", "month"] = Query("month"),
    format: Literal["pdf", "json"] = Query("pdf"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate and download Business Intelligence Report as PDF or JSON. PRO+ only."""
    analysis, meta = await _build_report(db, current_user, location_id, period)

    if format == "json":
        return JSONResponse({"analysis": analysis, "meta": meta})

    # PDF — run in thread pool: WeasyPrint is synchronous and CPU-heavy
    from app.services.pdf_report import generate_pdf_bytes

    pdf_bytes = await asyncio.to_thread(generate_pdf_bytes, analysis, meta)

    loc_slug = (meta.get("location_name") or "all").lower().replace(" ", "-")[:20]
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"report_{loc_slug}_{period}_{today_str}.pdf"

    return FastAPIResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
