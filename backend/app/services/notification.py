import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def send_telegram(message: str) -> bool:
    """Send a message via Telegram Bot API. Returns True on success."""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        logger.debug("Telegram not configured, skipping notification")
        return False

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                url,
                json={
                    "chat_id": settings.TELEGRAM_CHAT_ID,
                    "text": message,
                    "parse_mode": "HTML",
                },
            )
            if resp.status_code != 200:
                logger.warning("Telegram API returned %s: %s", resp.status_code, resp.text)
                return False
            return True
    except Exception as e:
        logger.error("Failed to send Telegram notification: %s", e)
        return False


async def notify_new_reviews(business_name: str, new_count: int, avg_rating: float) -> None:
    """Send a Telegram alert for new reviews."""
    stars = "⭐" * round(avg_rating)
    message = (
        f"<b>🔔 New reviews — {business_name}</b>\n\n"
        f"📊 {new_count} new review(s)\n"
        f"Rating: {stars} ({avg_rating:.1f}/5)\n\n"
        f"<a href='{settings.FRONTEND_URL}/dashboard/reviews'>View and respond →</a>"
    )
    await send_telegram(message)
