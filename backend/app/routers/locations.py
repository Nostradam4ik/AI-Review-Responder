from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.location import Location
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User
from app.services.gmb_service import get_gmb_service

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("/")
async def list_locations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all saved locations for current user."""
    result = await db.execute(
        select(Location).where(Location.user_id == current_user.id)
    )
    locations = result.scalars().all()
    return [
        {
            "id": str(loc.id),
            "gmb_location_id": loc.gmb_location_id,
            "name": loc.name,
            "address": loc.address,
            "is_active": loc.is_active,
        }
        for loc in locations
    ]


@router.post("/sync")
async def sync_locations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch locations from GMB API and sync to DB."""
    if not current_user.access_token:
        return {"synced": 0, "new": 0, "locations": [],
                "message": "No Google account connected. Please sign in with Google to sync locations."}

    try:
        gmb = await get_gmb_service(current_user, db)
        gmb_locations = await gmb.get_locations()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GMB API error: {str(e)}")

    # Determine max_locations from the user's active plan (trial = unlimited)
    count_result = await db.execute(
        select(func.count()).where(
            Location.user_id == current_user.id,
            Location.is_active == True,  # noqa: E712
        )
    )
    current_count = count_result.scalar() or 0

    sub_result = await db.execute(
        select(Subscription).where(Subscription.user_id == current_user.id)
    )
    sub = sub_result.scalar_one_or_none()

    max_locations = 999  # unlimited for trial / no subscription

    if sub and sub.status == "active":
        plan_result = await db.execute(select(Plan).where(Plan.id == sub.plan_id))
        plan = plan_result.scalar_one_or_none()
        if plan:
            max_locations = plan.features.get("max_locations", 1)

    synced = []
    for loc_data in gmb_locations:
        result = await db.execute(
            select(Location).where(
                Location.gmb_location_id == loc_data["gmb_location_id"],
                Location.user_id == current_user.id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            if current_count >= max_locations:
                raise HTTPException(status_code=402, detail="location_limit_reached")
            location = Location(
                user_id=current_user.id,
                gmb_location_id=loc_data["gmb_location_id"],
                name=loc_data["name"],
                address=loc_data["address"],
            )
            db.add(location)
            current_count += 1
            synced.append(loc_data["name"])
        else:
            existing.name = loc_data["name"]
            existing.address = loc_data["address"]

    await db.commit()
    return {"synced": len(gmb_locations), "new": len(synced), "locations": synced}
