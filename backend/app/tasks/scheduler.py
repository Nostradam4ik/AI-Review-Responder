import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.database import async_session
from app.models.location import Location
from app.models.user import User
from app.services.gmb_service import get_gmb_service
from app.services.notification import notify_new_reviews

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def sync_all_reviews() -> None:
    """
    Background job: for every active user → sync reviews for each active location
    → send Telegram alert if new reviews were found.
    Runs every 30 minutes.
    """
    logger.info("Starting scheduled review sync...")

    async with async_session() as db:
        result = await db.execute(
            select(User).where(User.access_token.isnot(None))
        )
        users = result.scalars().all()

        for user in users:
            try:
                await _sync_user_reviews(user, db)
            except Exception as e:
                logger.error("Error syncing reviews for user %s: %s", user.id, e)

    logger.info("Scheduled review sync complete.")


async def _sync_user_reviews(user: User, db) -> None:
    result = await db.execute(
        select(Location).where(
            Location.user_id == user.id,
            Location.is_active == True,  # noqa: E712
        )
    )
    locations = result.scalars().all()

    if not locations:
        return

    gmb = await get_gmb_service(user, db)
    total_new = 0
    total_rating = 0.0

    for location in locations:
        try:
            new_reviews = await gmb.sync_reviews(location, db)
            if new_reviews:
                total_new += len(new_reviews)
                total_rating += sum(r.rating for r in new_reviews)
        except Exception as e:
            logger.warning(
                "Failed to sync reviews for location %s: %s", location.gmb_location_id, e
            )

    await db.commit()

    if total_new > 0:
        avg_rating = total_rating / total_new
        business_name = user.business_name or user.email
        await notify_new_reviews(business_name, total_new, avg_rating, user=user)
        logger.info(
            "Notified %s of %d new review(s)", business_name, total_new
        )


def start_scheduler() -> None:
    scheduler.add_job(
        sync_all_reviews,
        trigger="interval",
        minutes=30,
        id="sync_reviews",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("APScheduler started — syncing reviews every 30 minutes")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")
