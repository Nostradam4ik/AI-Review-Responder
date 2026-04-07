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


async def send_welcome_email(to_email: str, user_name: str, trial_days: int = 14) -> None:
    """Send welcome email with trial details after account creation."""
    if not settings.RESEND_API_KEY:
        logger.info("RESEND_API_KEY not set — skipping welcome email to %s", to_email)
        return

    _init_resend()
    dashboard_url = f"{settings.FRONTEND_URL}/dashboard"
    onboarding_url = f"{settings.FRONTEND_URL}/onboarding"

    try:
        resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": [to_email],
            "subject": "Welcome to AI Review Responder 🎉",
            "html": f"""
            <div style="font-family:sans-serif;max-width:520px;margin:0 auto">
              <h2>Welcome, {user_name}!</h2>
              <p>Your account is ready. You have a <strong>{trial_days}-day free trial</strong>
              with full access to all Pro features — no credit card required.</p>
              <p>To get started, connect your Google Business Profile so we can start
              syncing and responding to your reviews automatically.</p>
              <a href="{onboarding_url}"
                 style="display:inline-block;background:#4f46e5;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;margin:16px 0">
                Connect Google Business
              </a>
              <p>Or go straight to your <a href="{dashboard_url}" style="color:#4f46e5">dashboard</a>
              to explore the product.</p>
              <p style="color:#888;font-size:12px">
                Questions? Reply to this email — we read every message.
              </p>
            </div>
            """,
        })
    except Exception as e:
        logger.warning("Failed to send welcome email to %s: %s", to_email, e)


async def send_trial_expiring_email(to_email: str, user_name: str, days_remaining: int) -> None:
    """Remind user their trial is ending soon and prompt them to upgrade."""
    if not settings.RESEND_API_KEY:
        logger.info("RESEND_API_KEY not set — skipping trial expiring email to %s", to_email)
        return

    _init_resend()
    billing_url = f"{settings.FRONTEND_URL}/dashboard/billing"
    urgency = "today" if days_remaining <= 1 else f"in {days_remaining} days"

    try:
        resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": [to_email],
            "subject": f"Your trial ends in {days_remaining} day(s) — choose a plan",
            "html": f"""
            <div style="font-family:sans-serif;max-width:520px;margin:0 auto">
              <h2>Your free trial expires {urgency}, {user_name}</h2>
              <p>After your trial ends, you'll lose access to AI response generation,
              Google Business sync, and review notifications.</p>
              <p><strong>Keep your access by choosing a plan:</strong></p>
              <ul style="color:#444;line-height:1.8">
                <li><strong>Starter €19/mo</strong> — 1 location, 100 AI responses/month</li>
                <li><strong>Pro €39/mo</strong> — 3 locations, unlimited responses,
                    CSV export, auto-publish, custom instructions</li>
                <li><strong>Agency €79/mo</strong> — 10 locations, everything in Pro</li>
              </ul>
              <a href="{billing_url}"
                 style="display:inline-block;background:#4f46e5;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;margin:16px 0">
                Choose a plan
              </a>
              <p style="color:#888;font-size:12px">
                No action needed to cancel — your account simply reverts to read-only
                if you don't upgrade.
              </p>
            </div>
            """,
        })
    except Exception as e:
        logger.warning("Failed to send trial expiring email to %s: %s", to_email, e)


async def send_subscription_confirmed_email(
    to_email: str, user_name: str, plan_name: str, amount: int
) -> None:
    """Confirm successful subscription activation and list unlocked features."""
    if not settings.RESEND_API_KEY:
        logger.info("RESEND_API_KEY not set — skipping subscription confirmed email to %s", to_email)
        return

    _init_resend()
    dashboard_url = f"{settings.FRONTEND_URL}/dashboard"

    try:
        resend.Emails.send({
            "from": settings.FROM_EMAIL,
            "to": [to_email],
            "subject": f"You're now on the {plan_name} plan ✅",
            "html": f"""
            <div style="font-family:sans-serif;max-width:520px;margin:0 auto">
              <h2>Subscription confirmed, {user_name}!</h2>
              <p>You're now on the <strong>{plan_name}</strong> plan (€{amount}/month).
              Thank you for your support!</p>
              <p><strong>What's now unlocked:</strong></p>
              <ul style="color:#444;line-height:1.8">
                <li>✅ AI response generation</li>
                <li>✅ Google Business sync &amp; auto-publish</li>
                <li>✅ Telegram review alerts</li>
                <li>✅ CSV export &amp; full analytics</li>
                <li>✅ Custom AI response instructions</li>
              </ul>
              <a href="{dashboard_url}"
                 style="display:inline-block;background:#4f46e5;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;margin:16px 0">
                Go to dashboard
              </a>
              <p style="color:#888;font-size:12px">
                Manage your subscription anytime from the Billing page.
                Reply to this email if you have any questions.
              </p>
            </div>
            """,
        })
    except Exception as e:
        logger.warning("Failed to send subscription confirmed email to %s: %s", to_email, e)
