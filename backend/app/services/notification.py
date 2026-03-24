import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def send_telegram(message: str, chat_id: str | None = None) -> bool:
    """Send a message via Telegram Bot API. Returns True on success.

    If chat_id is provided, sends to that specific user.
    Otherwise falls back to the global TELEGRAM_CHAT_ID env var.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.debug("Telegram not configured, skipping notification")
        return False

    target = chat_id or settings.TELEGRAM_CHAT_ID
    if not target:
        logger.debug("No chat_id and no global TELEGRAM_CHAT_ID, skipping")
        return False

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                url,
                json={
                    "chat_id": target,
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


async def notify_new_reviews(
    business_name: str,
    new_count: int,
    avg_rating: float,
    chat_id: str | None = None,
) -> None:
    """Send a Telegram alert for new reviews.

    Uses per-user chat_id if provided, else global fallback.
    """
    stars = "⭐" * round(avg_rating)
    message = (
        f"<b>🔔 New reviews — {business_name}</b>\n\n"
        f"📊 {new_count} new review(s)\n"
        f"Rating: {stars} ({avg_rating:.1f}/5)\n\n"
        f"<a href='{settings.FRONTEND_URL}/dashboard/reviews'>View and respond →</a>"
    )
    await send_telegram(message, chat_id=chat_id)
