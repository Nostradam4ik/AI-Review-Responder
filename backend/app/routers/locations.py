from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.location import Location
from app.models.user import User
from app.services.gmb_service import GMBService

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

    gmb = GMBService(current_user.access_token)
    try:
        gmb_locations = await gmb.get_locations()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GMB API error: {str(e)}")

    synced = []
    for loc_data in gmb_locations:
        result = await db.execute(
            select(Location).where(Location.gmb_location_id == loc_data["gmb_location_id"])
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            location = Location(
                user_id=current_user.id,
                gmb_location_id=loc_data["gmb_location_id"],
                name=loc_data["name"],
                address=loc_data["address"],
            )
            db.add(location)
            synced.append(loc_data["name"])
        else:
            existing.name = loc_data["name"]
            existing.address = loc_data["address"]

    await db.flush()
    return {"synced": len(gmb_locations), "new": len(synced), "locations": synced}
