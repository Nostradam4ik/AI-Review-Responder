import csv
import io
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_plan_feature
from app.database import get_db
from app.models.location import Location
from app.models.review import Review
from app.models.user import User
from app.services.gmb_service import GMBService, get_gmb_service

router = APIRouter(prefix="/reviews", tags=["reviews"])


class UpdateStatusBody(BaseModel):
    status: str


DEMO_REVIEWS = [
    {
        "gmb_review_id": "demo_r001",
        "author_name": "Marie Dupont",
        "rating": 5,
        "comment": "Excellent restaurant ! La cuisine est vraiment exceptionnelle, les plats sont savoureux et la présentation est magnifique. Le service est impeccable et l'atmosphère très agréable. Je recommande vivement !",
        "language": "fr",
        "days_ago": 2,
    },
    {
        "gmb_review_id": "demo_r002",
        "author_name": "Jean-Luc Moreau",
        "rating": 4,
        "comment": "Très bon restaurant dans l'ensemble. La nourriture était délicieuse et le service attentif. Seul bémol : l'attente un peu longue entre les plats. Mais on y reviendra sans hésiter.",
        "language": "fr",
        "days_ago": 5,
    },
    {
        "gmb_review_id": "demo_r003",
        "author_name": "Sophie Bernard",
        "rating": 3,
        "comment": "Expérience mitigée. L'entrée était excellente mais le plat principal était trop salé. Le cadre est sympa et le personnel souriant. Peut mieux faire pour le prix demandé.",
        "language": "fr",
        "days_ago": 9,
    },
    {
        "gmb_review_id": "demo_r004",
        "author_name": "Robert Girard",
        "rating": 2,
        "comment": "Déçu par cette visite. Nous avons attendu 45 minutes pour être servis. Le steak était trop cuit malgré notre demande saignant. La facture ne correspondait pas à la qualité du repas.",
        "language": "fr",
        "days_ago": 14,
    },
    {
        "gmb_review_id": "demo_r005",
        "author_name": "Isabelle Petit",
        "rating": 5,
        "comment": "Coup de cœur pour ce bistrot ! Ambiance authentique parisienne, cuisine traditionnelle revisitée avec talent. Le foie gras et le magret de canard étaient divins. Prix très raisonnables.",
        "language": "fr",
        "days_ago": 18,
    },
    {
        "gmb_review_id": "demo_r006",
        "author_name": "James Wilson",
        "rating": 1,
        "comment": "Terrible experience. Staff was rude and the food was cold. Waited over an hour for our order. Will not be returning.",
        "language": "en",
        "days_ago": 22,
    },
]


@router.post("/seed-demo", status_code=201)
async def seed_demo_reviews(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Seed demo reviews for the current user to explore the product."""
    from datetime import datetime, timezone, timedelta

    # Skip if the user already has real GMB locations connected
    real_loc_result = await db.execute(
        select(Location).where(
            Location.user_id == current_user.id,
            Location.is_active == True,  # noqa: E712
            ~Location.gmb_location_id.like(f"demo_%"),
        )
    )
    if real_loc_result.scalar_one_or_none() is not None:
        return {"created": 0, "message": "Real locations already connected"}

    # Get or create a demo location for this user
    loc_result = await db.execute(
        select(Location).where(
            Location.user_id == current_user.id,
            Location.gmb_location_id == f"demo_{current_user.id}",
        )
    )
    location = loc_result.scalar_one_or_none()

    if location is None:
        location = Location(
            user_id=current_user.id,
            gmb_location_id=f"demo_{current_user.id}",
            name=current_user.business_name or "Mon Établissement",
            address="12 Rue de la Paix, 75001 Paris",
            is_active=True,
        )
        db.add(location)
        await db.flush()
        await db.refresh(location)

    # Insert reviews (skip existing)
    created = 0
    for r in DEMO_REVIEWS:
        existing_review = await db.execute(
            select(Review).where(
                Review.location_id == location.id,
                Review.gmb_review_id == f"demo_{current_user.id}_{r['gmb_review_id']}",
            )
        )
        if existing_review.scalar_one_or_none() is not None:
            continue

        review = Review(
            location_id=location.id,
            gmb_review_id=f"demo_{current_user.id}_{r['gmb_review_id']}",
            author_name=r["author_name"],
            rating=r["rating"],
            comment=r["comment"],
            language=r["language"],
            review_date=datetime.now(timezone.utc) - timedelta(days=r["days_ago"]),
            status="pending",
        )
        db.add(review)
        created += 1

    await db.flush()
    await db.commit()
    return {"created": created, "location": location.name}


@router.post("/test-telegram")
async def test_telegram(current_user: User = Depends(get_current_user)):
    """Send a test Telegram notification to verify the bot is configured correctly."""
    from app.services.notification import send_telegram
    name = current_user.business_name or current_user.email
    ok = await send_telegram(
        f"✅ <b>Telegram connected!</b>\n\n"
        f"Account: {name}\n"
        f"Bot is working — you'll receive review alerts here."
    )
    if ok:
        return {"ok": True, "message": "Telegram notification sent successfully."}
    return {"ok": False, "message": "Failed — check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env"}


@router.post("/seed-mock", status_code=201)
async def seed_mock(db: AsyncSession = Depends(get_db)):
    """Seed mock data for development/testing. Only available in development environment."""
    from app.config import settings
    if settings.ENVIRONMENT not in ("development", "test"):
        raise HTTPException(status_code=403, detail="Only available in development")

    from app.scripts.seed_mock_data import seed_mock_data
    result = await seed_mock_data(db)
    return result


def _build_review_query(location_ids, status=None, location_id=None, date_from=None, date_to=None):
    query = select(Review).where(Review.location_id.in_(location_ids))
    if status:
        query = query.where(Review.status == status)
    if location_id:
        query = query.where(Review.location_id == uuid.UUID(location_id))
    if date_from:
        query = query.where(Review.review_date >= date_from)
    if date_to:
        query = query.where(Review.review_date <= date_to)
    return query


@router.get("/export/csv")
async def export_reviews_csv(
    location_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    current_user: User = Depends(require_plan_feature("export_csv")),
    db: AsyncSession = Depends(get_db),
):
    """Export reviews as a CSV file. PRO+ only."""
    from app.models.response import Response as ReviewResponse
    locs_result = await db.execute(
        select(Location).where(Location.user_id == current_user.id)
    )
    locations = {loc.id: loc for loc in locs_result.scalars().all()}
    if not locations:
        return StreamingResponse(io.StringIO(""), media_type="text/csv")

    query = _build_review_query(
        list(locations.keys()),
        status=status,
        location_id=str(location_id) if location_id else None,
        date_from=date_from,
        date_to=date_to,
    )
    query = query.order_by(Review.review_date.desc())
    result = await db.execute(query)
    reviews = result.scalars().all()

    # Fetch responses for all reviews in one query
    review_ids = [r.id for r in reviews]
    resp_result = await db.execute(
        select(ReviewResponse).where(ReviewResponse.review_id.in_(review_ids))
    )
    responses_by_review = {r.review_id: r for r in resp_result.scalars().all()}

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["date", "author", "rating", "review_text", "response_text", "status", "location"])
    for r in reviews:
        resp = responses_by_review.get(r.id)
        resp_text = (resp.final_text or resp.ai_draft) if resp else ""
        writer.writerow([
            r.review_date.strftime("%Y-%m-%d") if r.review_date else "",
            r.author_name or "",
            r.rating,
            r.comment or "",
            resp_text,
            r.status,
            locations.get(r.location_id, type("L", (), {"name": ""})()).name,
        ])

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=reviews.csv"},
    )


@router.get("/")
async def list_reviews(
    status: str | None = Query(None, description="Filter by status: pending/responded/ignored"),
    location_id: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    sort: str | None = Query(None, description="Sort order: 'priority' or default (date desc)"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List reviews for the current user, with optional filters."""
    locs_result = await db.execute(
        select(Location.id).where(Location.user_id == current_user.id)
    )
    location_ids = [row[0] for row in locs_result.all()]

    if not location_ids:
        return {"reviews": [], "total": 0}

    query = _build_review_query(location_ids, status=status, location_id=location_id,
                                date_from=date_from, date_to=date_to)

    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()

    # Sort
    if sort == "priority":
        query = query.order_by(Review.priority_score.desc(), Review.review_date.desc())
    else:
        query = query.order_by(Review.review_date.desc())

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    reviews = result.scalars().all()

    return {
        "reviews": [
            {
                "id": str(r.id),
                "location_id": str(r.location_id),
                "gmb_review_id": r.gmb_review_id,
                "author_name": r.author_name,
                "rating": r.rating,
                "comment": r.comment,
                "language": r.language,
                "review_date": r.review_date.isoformat() if r.review_date else None,
                "status": r.status,
                "priority_score": r.priority_score,
                "synced_at": r.synced_at.isoformat(),
            }
            for r in reviews
        ],
        "total": total,
    }


@router.post("/sync")
async def sync_reviews(
    location_id: str | None = Query(None, description="Sync specific location, or all if omitted"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sync reviews from GMB for one or all locations."""
    if not current_user.access_token:
        return {
            "synced_locations": 0,
            "new_reviews": 0,
            "message": "No Google account connected. Please sign in with Google to sync reviews.",
        }

    # Get locations to sync
    query = select(Location).where(
        Location.user_id == current_user.id,
        Location.is_active == True,  # noqa: E712
    )
    if location_id:
        query = query.where(Location.id == location_id)

    result = await db.execute(query)
    locations = result.scalars().all()

    if not locations:
        return {
            "synced_locations": 0,
            "new_reviews": 0,
            "message": "No active locations found. Go to Settings to sync your Google Business locations.",
        }

    gmb = await get_gmb_service(current_user, db)
    total_new = 0
    for location in locations:
        new_reviews = await gmb.sync_reviews(location, db)
        total_new += len(new_reviews)

    await db.commit()
    return {"synced_locations": len(locations), "new_reviews": total_new}


@router.patch("/{review_id}/status")
async def update_review_status(
    review_id: uuid.UUID,
    body: UpdateStatusBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update review status (pending/responded/ignored)."""
    if body.status not in ("pending", "responded", "ignored"):
        raise HTTPException(status_code=400, detail="Invalid status")

    review = await db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")

    # Verify ownership
    location = await db.get(Location, review.location_id)
    if location is None or location.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    review.status = body.status
    await db.commit()
    await db.refresh(review)
    return {"id": str(review_id), "status": body.status}
