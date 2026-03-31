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


async def _send_review_email(to_email: str, business_name: str, new_count: int, avg_rating: float) -> bool:
    """Send a new-review alert email via Resend. Returns True on success."""
    if not settings.RESEND_API_KEY:
        logger.debug("RESEND_API_KEY not set — skipping review alert email")
        return False

    try:
        import resend
        resend.api_key = settings.RESEND_API_KEY

        stars_html = "⭐" * round(avg_rating)
        dashboard_url = f"{settings.FRONTEND_URL}/dashboard/reviews"

        resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": [to_email],
            "subject": f"🔔 New reviews — {business_name}",
            "html": f"""
            <div style="font-family:sans-serif;max-width:480px;margin:0 auto;background:#0A0A0F;color:#e2e8f0;padding:32px;border-radius:12px">
              <h2 style="color:#fff;margin-bottom:8px">🔔 New reviews — {business_name}</h2>
              <p style="color:#94a3b8;margin-bottom:16px">You have new reviews waiting for a response.</p>

              <div style="background:#111118;border:1px solid #2A2A3E;border-radius:8px;padding:20px;margin-bottom:20px">
                <p style="margin:0 0 4px;color:#94a3b8;font-size:14px">📊 {new_count} new review(s)</p>
                <p style="margin:0;color:#94a3b8;font-size:14px">Rating: {stars_html} ({avg_rating:.1f}/5)</p>
              </div>

              <a href="{dashboard_url}"
                 style="display:inline-block;background:#4f46e5;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px">
                View and respond →
              </a>

              <p style="color:#475569;font-size:11px;margin-top:24px">
                Connect Telegram in Settings to receive instant notifications instead of email.
              </p>
            </div>
            """,
        })
        return True
    except Exception as e:
        logger.error("Failed to send review alert email to %s: %s", to_email, e)
        return False


async def notify_new_reviews(
    business_name: str,
    new_count: int,
    avg_rating: float,
    user=None,
    chat_id: str | None = None,
) -> None:
    """Send a new-review alert via Telegram (per-user) or email fallback.

    Priority:
    1. user.telegram_chat_id → Telegram
    2. chat_id param → Telegram
    3. user.email → email via Resend
    4. global TELEGRAM_CHAT_ID → Telegram (legacy)
    """
    # Determine Telegram target
    telegram_target = None
    if user and getattr(user, "telegram_chat_id", None):
        telegram_target = user.telegram_chat_id
    elif chat_id:
        telegram_target = chat_id

    if telegram_target:
        stars = "⭐" * round(avg_rating)
        message = (
            f"<b>🔔 New reviews — {business_name}</b>\n\n"
            f"📊 {new_count} new review(s)\n"
            f"Rating: {stars} ({avg_rating:.1f}/5)\n\n"
            f"<a href='{settings.FRONTEND_URL}/dashboard/reviews'>View and respond →</a>"
        )
        sent = await send_telegram(message, chat_id=telegram_target)
        if sent:
            return

    # No Telegram → try email
    if user and getattr(user, "email", None):
        sent = await _send_review_email(user.email, business_name, new_count, avg_rating)
        if sent:
            return

    # Legacy global fallback
    if settings.TELEGRAM_CHAT_ID:
        stars = "⭐" * round(avg_rating)
        message = (
            f"<b>🔔 New reviews — {business_name}</b>\n\n"
            f"📊 {new_count} new review(s)\n"
            f"Rating: {stars} ({avg_rating:.1f}/5)\n\n"
            f"<a href='{settings.FRONTEND_URL}/dashboard/reviews'>View and respond →</a>"
        )
        await send_telegram(message)
