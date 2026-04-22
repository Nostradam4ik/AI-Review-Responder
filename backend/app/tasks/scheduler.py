import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.database import async_session
from app.models.location import Location
from app.models.subscription import Subscription
from app.models.user import User
from app.services.email_service import send_trial_expiring_email
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
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(User)
            .join(Subscription, Subscription.user_id == User.id)
            .where(
                User.access_token.isnot(None),
                Subscription.status.in_(["active", "trialing"]),
                ~(
                    (Subscription.status == "trialing") &
                    (Subscription.trial_end < now)
                ),
            )
        )
        user_ids = [u.id for u in result.scalars().all()]

    for user_id in user_ids:
        try:
            async with async_session() as db:
                user = await db.get(User, user_id)
                if user:
                    await _sync_user_reviews(user, db)
        except Exception as e:
            logger.error("Error syncing reviews for user %s: %s", user_id, e, exc_info=True)

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


async def check_trial_expirations() -> None:
    """Daily job: email users whose trial ends in exactly 3 or 1 day."""
    now = datetime.now(timezone.utc)
    remind_days = {1, 3}
    logger.info("Checking trial expirations...")

    async with async_session() as db:
        result = await db.execute(
            select(User, Subscription)
            .join(Subscription, Subscription.user_id == User.id)
            .where(
                Subscription.status == "trialing",
                Subscription.trial_end.isnot(None),
            )
        )
        rows = result.all()

    for user, sub in rows:
        days_left = (sub.trial_end - now).days
        if days_left in remind_days:
            name = user.business_name or user.email
            try:
                await send_trial_expiring_email(user.email, name, days_left)
                logger.info(
                    "Sent trial expiring email to %s (%d day(s) left)", user.email, days_left
                )
            except Exception as e:
                logger.warning(
                    "Failed to send trial expiring email to %s: %s", user.email, e
                )


async def cleanup_analytics_cache() -> None:
    """Delete analytics_cache rows older than 7 days."""
    from app.models.analytics_cache import AnalyticsCache
    from sqlalchemy import delete as sa_delete

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    async with async_session() as db:
        await db.execute(
            sa_delete(AnalyticsCache).where(AnalyticsCache.expires_at < cutoff)
        )
        await db.commit()


def start_scheduler() -> None:
    scheduler.add_job(
        sync_all_reviews,
        trigger="interval",
        minutes=30,
        id="sync_reviews",
        replace_existing=True,
    )
    scheduler.add_job(
        check_trial_expirations,
        trigger="interval",
        hours=24,
        id="trial_expirations",
        replace_existing=True,
    )
    scheduler.add_job(
        cleanup_analytics_cache,
        trigger="cron",
        hour=3,
        minute=0,
        id="cleanup_analytics_cache",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("APScheduler started — syncing reviews every 30 minutes, trial checks every 24 hours, analytics cache cleanup daily at 03:00 UTC")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")
