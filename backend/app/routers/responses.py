import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.limiter import limiter
from app.core.usage_limit import check_usage_limit
from app.database import get_db
from app.models.location import Location
from app.models.response import Response
from app.models.review import Review
from app.models.usage_log import UsageLog
from app.models.user import User
from app.schemas.response import ResponseCreate, ResponseEdit, ResponseRead
from app.services.ai_service import generate_and_save
from app.services.gmb_service import get_gmb_service

router = APIRouter(prefix="/responses", tags=["responses"])

# ── Per-user sliding-window rate limiter ──────────────────────────────────────

RESPONSE_RATE_LIMITS: dict[str, tuple[int, int]] = {
    "free":    (5,  60),
    "starter": (10, 60),
    "pro":     (20, 60),
    "agency":  (60, 60),
}

# In-memory sliding window: user_id → list of call timestamps
_rate_windows: dict[str, list[float]] = defaultdict(list)


def _check_sliding_window(user_id: str, max_calls: int, window_sec: int) -> None:
    """Raise 429 if the user has exceeded max_calls within the last window_sec seconds."""
    now = time.time()
    key = str(user_id)
    # Evict timestamps outside the window
    _rate_windows[key] = [t for t in _rate_windows[key] if now - t < window_sec]
    if len(_rate_windows[key]) >= max_calls:
        raise HTTPException(
            status_code=429,
            headers={"Retry-After": str(window_sec)},
            detail={
                "error": "rate_limit_exceeded",
                "limit": f"{max_calls} requests per {window_sec}s",
                "retry_after": window_sec,
            },
        )
    _rate_windows[key].append(now)


async def _get_review_with_auth(
    review_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> Review:
    """Helper: fetch review and verify it belongs to current user."""
    review = await db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")

    location = await db.get(Location, review.location_id)
    if location is None or location.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return review


@router.post("/generate", response_model=ResponseRead)
@limiter.limit("20/minute")
async def generate_response(
    request: Request,
    body: ResponseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate an AI draft response for a review (usage limit checked)."""
    # Per-plan sliding-window rate limit (in-memory, single-server)
    from app.core.report_limit import _get_user_plan_name
    plan_name = await _get_user_plan_name(current_user, db)
    max_calls, window = RESPONSE_RATE_LIMITS.get(plan_name, (5, 60))
    _check_sliding_window(str(current_user.id), max_calls, window)

    await _get_review_with_auth(body.review_id, current_user, db)
    await check_usage_limit(current_user, "ai_generate", db)

    tone = body.tone or current_user.tone_preference or "warm"
    extra = current_user.response_instructions or ""
    response = await generate_and_save(body.review_id, db, tone=tone, extra_instructions=extra)

    # Auto-publish if user has it enabled and has a Google token
    if current_user.auto_publish and current_user.access_token:
        import logging as _logging
        _logger = _logging.getLogger(__name__)
        try:
            await check_usage_limit(current_user, "ai_publish", db)
            review = await db.get(Review, body.review_id)
            location = await db.get(Location, review.location_id)
            gmb = await get_gmb_service(current_user, db)
            published = await gmb.publish_response(
                gmb_location_id=location.gmb_location_id,
                review_id=review.gmb_review_id,
                response_text=response.ai_draft,
            )
            if published:
                response.published_at = datetime.now(timezone.utc)
                review.status = "responded"
                db.add(UsageLog(
                    user_id=current_user.id,
                    action_type="ai_publish",
                    billing_period=datetime.now(timezone.utc).strftime("%Y-%m"),
                ))
                await db.commit()
                await db.refresh(response)
        except HTTPException as exc:
            # Usage limit exceeded or trial expired — save draft but skip publish
            _logger.warning("Auto-publish skipped for user %s: %s", current_user.id, exc.detail)

    return response


@router.put("/{response_id}", response_model=ResponseRead)
async def edit_response(
    response_id: uuid.UUID,
    body: ResponseEdit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save an edited version of the AI draft."""
    response = await db.get(Response, response_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Response not found")

    await _get_review_with_auth(response.review_id, current_user, db)

    response.final_text = body.final_text
    response.was_edited = True
    await db.commit()
    await db.refresh(response)
    return response


@router.post("/{response_id}/publish", response_model=ResponseRead)
async def publish_response(
    response_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Publish the response to Google My Business (usage limit checked)."""
    response = await db.get(Response, response_id)
    if response is None:
        raise HTTPException(status_code=404, detail="Response not found")

    review = await _get_review_with_auth(response.review_id, current_user, db)
    await check_usage_limit(current_user, "ai_publish", db)

    location = await db.get(Location, review.location_id)

    if not current_user.access_token:
        raise HTTPException(status_code=400, detail="No Google access token")

    text_to_publish = response.final_text or response.ai_draft

    gmb = await get_gmb_service(current_user, db)
    success = await gmb.publish_response(
        gmb_location_id=location.gmb_location_id,
        review_id=review.gmb_review_id,
        response_text=text_to_publish,
    )

    if not success:
        raise HTTPException(status_code=502, detail="Failed to publish to GMB")

    response.published_at = datetime.now(timezone.utc)
    review.status = "responded"
    await db.commit()
    await db.refresh(response)
    return response


@router.get("/review/{review_id}", response_model=ResponseRead | None)
async def get_response_for_review(
    review_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the existing draft/published response for a review."""
    await _get_review_with_auth(review_id, current_user, db)

    result = await db.execute(
        select(Response).where(Response.review_id == review_id)
    )
    return result.scalar_one_or_none()
