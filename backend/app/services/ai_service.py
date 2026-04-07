import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location
from app.models.response import Response
from app.models.review import Review
from app.models.usage_log import UsageLog
from app.services.llm.base import ReviewContext
from app.services.llm.factory import get_llm_provider


async def generate_and_save(
    review_id: uuid.UUID,
    db: AsyncSession,
    tone: str = "warm",
    extra_instructions: str = "",
) -> Response:
    """Generate an AI response for a review and save it as a draft."""
    review = await db.get(Review, review_id)
    if review is None:
        raise ValueError(f"Review {review_id} not found")

    location = await db.get(Location, review.location_id)
    business_name = location.name if location else "our business"

    provider = get_llm_provider()
    context = ReviewContext(
        review_text=review.comment or "",
        business_name=business_name,
        rating=review.rating,
        tone=tone,
        extra_instructions=extra_instructions,
    )

    ai_text = await provider.generate_response(context)

    # Check if a draft already exists for this review
    result = await db.execute(
        select(Response).where(Response.review_id == review_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.ai_draft = ai_text
        existing.tone_used = tone
        existing.model_used = provider.MODEL
        existing.was_edited = False
        existing.final_text = None
        existing.published_at = None
        return existing

    response = Response(
        review_id=review_id,
        ai_draft=ai_text,
        tone_used=tone,
        model_used=provider.MODEL,
    )
    db.add(response)
    await db.flush()
    await db.refresh(response)

    if location:
        period = datetime.now(timezone.utc).strftime("%Y-%m")
        db.add(UsageLog(
            user_id=location.user_id,
            action_type="ai_generate",
            billing_period=period,
        ))
        await db.flush()

    return response
