"""Email sending via Resend."""
import logging

import resend

from app.config import settings

logger = logging.getLogger(__name__)


def _init_resend() -> None:
    resend.api_key = settings.RESEND_API_KEY


async def send_verification_email(to_email: str, token: str) -> None:
    if not settings.RESEND_API_KEY:
        logger.info("RESEND_API_KEY not set — skipping verification email to %s", to_email)
        return

    _init_resend()
    verify_url = f"{settings.APP_URL}/verify-email?token={token}"

    try:
        resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": [to_email],
            "subject": "Verify your email — AI Review Responder",
            "html": f"""
            <div style="font-family:sans-serif;max-width:480px;margin:0 auto">
              <h2>Welcome to AI Review Responder!</h2>
              <p>Click the button below to verify your email address and activate your account.</p>
              <a href="{verify_url}"
                 style="display:inline-block;background:#2563eb;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;margin:16px 0">
                Verify Email
              </a>
              <p style="color:#888;font-size:12px">Link expires in 1 hour. If you didn't register, ignore this email.</p>
            </div>
            """,
        })
    except Exception as e:
        # Log but never crash registration because of an email delivery issue
        logger.warning("Failed to send verification email to %s: %s", to_email, e)


async def send_reset_email(to_email: str, token: str) -> None:
    if not settings.RESEND_API_KEY:
        logger.info("RESEND_API_KEY not set — skipping reset email to %s", to_email)
        return

    _init_resend()
    reset_url = f"{settings.APP_URL}/reset-password?token={token}"

    try:
        resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": [to_email],
            "subject": "Reset your password — AI Review Responder",
            "html": f"""
            <div style="font-family:sans-serif;max-width:480px;margin:0 auto">
              <h2>Password Reset</h2>
              <p>Click the button below to reset your password. This link expires in 1 hour.</p>
              <a href="{reset_url}"
                 style="display:inline-block;background:#2563eb;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;margin:16px 0">
                Reset Password
              </a>
              <p style="color:#888;font-size:12px">If you didn't request this, ignore this email.</p>
            </div>
            """,
        })
    except Exception as e:
        logger.warning("Failed to send reset email to %s: %s", to_email, e)


async def send_payment_failed_email(to_email: str, plan_name: str) -> None:
    """Notify user their payment failed and they lost access."""
    if not settings.RESEND_API_KEY:
        logger.info("RESEND_API_KEY not set — skipping payment failed email to %s", to_email)
        return

    _init_resend()
    subject = "Payment failed — your subscription has been paused"
    html = f"""
    <div style="font-family: sans-serif; max-width: 520px; margin: 0 auto;">
        <h2 style="color: #a12c7b;">Payment failed</h2>
        <p>Hi,</p>
        <p>We couldn't process your payment for the <strong>{plan_name}</strong> plan.</p>
        <p>Your account has been temporarily downgraded to the free tier.
        To restore full access, please update your payment method.</p>
        <p>
            <a href="{settings.FRONTEND_URL}/dashboard/billing"
               style="background:#01696f;color:white;padding:10px 20px;
                      border-radius:6px;text-decoration:none;display:inline-block;">
                Update payment method
            </a>
        </p>
        <p style="color:#7a7974;font-size:13px;">
            If you need help, reply to this email.
        </p>
    </div>
    """

    try:
        resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": html,
        })
    except Exception as e:
        logger.warning("Failed to send payment failed email to %s: %s", to_email, e)
