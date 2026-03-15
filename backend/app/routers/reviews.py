from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.location import Location
from app.models.review import Review
from app.models.user import User
from app.services.gmb_service import GMBService

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/")
async def list_reviews(
    status: str | None = Query(None, description="Filter by status: pending/responded/ignored"),
    location_id: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List reviews for the current user, with optional filters."""
    # Get user's location IDs
    locs_result = await db.execute(
        select(Location.id).where(Location.user_id == current_user.id)
    )
    location_ids = [row[0] for row in locs_result.all()]

    if not location_ids:
        return {"reviews": [], "total": 0}

    query = select(Review).where(Review.location_id.in_(location_ids))

    if status:
        query = query.where(Review.status == status)
    if location_id:
        query = query.where(Review.location_id == location_id)

    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()

    # Paginate
    query = query.order_by(Review.review_date.desc()).offset(offset).limit(limit)
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
        raise HTTPException(status_code=400, detail="No Google access token found")

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
        raise HTTPException(status_code=404, detail="No active locations found")

    gmb = GMBService(current_user.access_token)
    total_new = 0
    for location in locations:
        new_reviews = await gmb.sync_reviews(location, db)
        total_new += len(new_reviews)

    return {"synced_locations": len(locations), "new_reviews": total_new}


@router.patch("/{review_id}/status")
async def update_review_status(
    review_id: str,
    status: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update review status (pending/responded/ignored)."""
    if status not in ("pending", "responded", "ignored"):
        raise HTTPException(status_code=400, detail="Invalid status")

    review = await db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")

    # Verify ownership
    location = await db.get(Location, review.location_id)
    if location is None or location.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    review.status = status
    return {"id": review_id, "status": status}
