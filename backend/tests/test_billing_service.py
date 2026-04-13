"""Tests for billing_service — edge cases not covered by test_billing.py.

Covers:
- invoice.payment_failed webhook
- create_portal_session (with / without Stripe customer)
- get_billing_status: expired trial, cancelled sub, no plan row
- checkout with invalid plan_id → 400
- Unknown webhook event → silent no-op
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.models.user import User
from app.services import billing_service


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_event(event_type: str, data_object: dict) -> dict:
    return {"type": event_type, "data": {"object": data_object}}


def _fake_stripe_sub(sub_id: str = "sub_x") -> MagicMock:
    now = datetime.now(timezone.utc)
    m = MagicMock()
    m.__getitem__ = lambda self, k: {
        "id": sub_id,
        "current_period_start": now.timestamp(),
        "current_period_end": (now + timedelta(days=30)).timestamp(),
    }.get(k)
    return m


# ── create_checkout_session — invalid plan ────────────────────────────────────

async def test_checkout_invalid_plan_raises_400(
    db_session: AsyncSession,
    test_user: User,
):
    """create_checkout_session with unknown plan_id → HTTPException 400."""
    from fastapi import HTTPException
    with patch("app.services.billing_service._init_stripe"):
        with pytest.raises(HTTPException) as exc:
            await billing_service.create_checkout_session(test_user, "diamond", db_session)
    assert exc.value.status_code == 400


# ── create_portal_session ─────────────────────────────────────────────────────

async def test_portal_session_no_customer_raises_400(
    db_session: AsyncSession,
    test_user: User,
    trial_subscription: Subscription,
):
    """Portal session without a Stripe customer → HTTPException 400."""
    from fastapi import HTTPException
    # trial_subscription has no stripe_customer_id
    assert trial_subscription.stripe_customer_id is None

    with patch("app.services.billing_service._init_stripe"):
        with pytest.raises(HTTPException) as exc:
            await billing_service.create_portal_session(test_user, db_session)
    assert exc.value.status_code == 400


async def test_portal_session_returns_url(
    db_session: AsyncSession,
    test_user: User,
    trial_subscription: Subscription,
):
    """Portal session with Stripe customer → returns portal URL."""
    trial_subscription.stripe_customer_id = "cus_portal123"
    await db_session.flush()

    mock_portal = MagicMock()
    mock_portal.__getitem__ = lambda self, k: "https://billing.stripe.com/portal/test" if k == "url" else None

    async def fake_to_thread(fn, *args, **kwargs):
        return mock_portal

    with patch("app.services.billing_service.asyncio.to_thread", side_effect=fake_to_thread), \
         patch("app.services.billing_service._init_stripe"), \
         patch("app.services.billing_service.settings") as ms:
        ms.APP_URL = "http://localhost:3000"

        url = await billing_service.create_portal_session(test_user, db_session)

    assert url == "https://billing.stripe.com/portal/test"


# ── handle_webhook — invoice.payment_failed ───────────────────────────────────

async def test_webhook_payment_failed_sets_past_due(
    db_session: AsyncSession,
    test_user: User,
    active_subscription: Subscription,
):
    """invoice.payment_failed → subscription becomes past_due, user plan = free."""
    active_subscription.stripe_subscription_id = "sub_fail123"
    await db_session.flush()

    event = _make_event("invoice.payment_failed", {"subscription": "sub_fail123"})

    with patch("stripe.Webhook.construct_event", return_value=event), \
         patch("app.services.billing_service._init_stripe"), \
         patch("app.services.billing_service.settings") as ms, \
         patch("app.services.email_service.send_payment_failed_email", new=AsyncMock()), \
         patch("app.services.notification.send_telegram", new=AsyncMock()):
        ms.STRIPE_WEBHOOK_SECRET = "whsec_test"
        ms.STRIPE_SECRET_KEY = "sk_test"
        ms.FRONTEND_URL = "http://localhost:3000"

        await billing_service.handle_webhook(b"payload", "sig", db_session)

    await db_session.refresh(active_subscription)
    assert active_subscription.status == "past_due"

    await db_session.refresh(test_user)
    assert test_user.plan == "free"


async def test_webhook_payment_failed_no_subscription_id_is_noop(
    db_session: AsyncSession,
):
    """invoice.payment_failed with no subscription field → silent no-op."""
    event = _make_event("invoice.payment_failed", {})  # no "subscription" key

    with patch("stripe.Webhook.construct_event", return_value=event), \
         patch("app.services.billing_service._init_stripe"), \
         patch("app.services.billing_service.settings") as ms:
        ms.STRIPE_WEBHOOK_SECRET = "whsec_test"
        ms.STRIPE_SECRET_KEY = "sk_test"

        # Should not raise
        await billing_service.handle_webhook(b"payload", "sig", db_session)


# ── handle_webhook — unknown event ────────────────────────────────────────────

async def test_webhook_unknown_event_is_noop(db_session: AsyncSession):
    """Unrecognised webhook event type → returns silently without error."""
    event = _make_event("some.future.event", {"foo": "bar"})

    with patch("stripe.Webhook.construct_event", return_value=event), \
         patch("app.services.billing_service._init_stripe"), \
         patch("app.services.billing_service.settings") as ms:
        ms.STRIPE_WEBHOOK_SECRET = "whsec_test"
        ms.STRIPE_SECRET_KEY = "sk_test"

        await billing_service.handle_webhook(b"payload", "sig", db_session)


# ── get_billing_status — edge cases ───────────────────────────────────────────

async def test_get_billing_status_expired_trial(
    db_session: AsyncSession,
    test_user: User,
    expired_trial_subscription: Subscription,
):
    """get_billing_status with an expired trial → is_trial_expired=True, is_trial=False."""
    status = await billing_service.get_billing_status(test_user, db_session)
    assert status["is_trial"] is False
    assert status["is_trial_expired"] is True
    assert status["trial_days_remaining"] is None


async def test_get_billing_status_cancelled_subscription(
    db_session: AsyncSession,
    test_user: User,
):
    """get_billing_status with a cancelled subscription reflects correct status."""
    sub = Subscription(
        user_id=test_user.id,
        plan_id="starter",
        status="cancelled",
    )
    db_session.add(sub)
    await db_session.flush()

    status = await billing_service.get_billing_status(test_user, db_session)
    assert status["subscription"]["status"] == "cancelled"
    assert status["is_trial"] is False
    assert status["pro_features_available"] is False


async def test_get_billing_status_active_sub_trusted_from_stripe(
    db_session: AsyncSession,
    test_user: User,
    active_subscription: Subscription,
):
    """get_billing_status trusts sub.status='active' from Stripe directly (no override)."""
    status = await billing_service.get_billing_status(test_user, db_session)
    assert status["subscription"]["status"] == "active"
    assert status["is_trial"] is False
    assert status["is_trial_expired"] is False


async def test_get_billing_status_unlimited_override(
    db_session: AsyncSession,
    test_user: User,
    active_subscription: Subscription,
):
    """responses_limit_override=-1 → ai_responses_limit is None (unlimited)."""
    active_subscription.responses_limit_override = -1
    await db_session.flush()

    status = await billing_service.get_billing_status(test_user, db_session)
    assert status["usage"]["ai_responses_limit"] is None


async def test_get_billing_status_custom_cap_override(
    db_session: AsyncSession,
    test_user: User,
    active_subscription: Subscription,
):
    """responses_limit_override=25 → ai_responses_limit=25."""
    active_subscription.responses_limit_override = 25
    await db_session.flush()

    status = await billing_service.get_billing_status(test_user, db_session)
    assert status["usage"]["ai_responses_limit"] == 25


# ── Unit tests: pure functions ────────────────────────────────────────────────

def test_price_id_unknown_plan():
    """_price_id_for_plan with unknown plan_id → HTTPException 400 (line 39)."""
    from fastapi import HTTPException
    from app.services.billing_service import _price_id_for_plan

    with patch("app.services.billing_service.settings") as ms:
        ms.STRIPE_PRICE_STARTER = ""
        ms.STRIPE_PRICE_PRO = ""
        ms.STRIPE_PRICE_AGENCY = ""
        with pytest.raises(HTTPException) as exc:
            _price_id_for_plan("unknown_xyz")

    assert exc.value.status_code == 400


def test_effective_ai_limit_none_inputs():
    """_effective_ai_limit(None, plan=None) → None (unlimited) (line 111)."""
    from app.services.billing_service import _effective_ai_limit

    result = _effective_ai_limit(None, plan=None)
    assert result is None


async def test_webhook_secret_missing(db_session: AsyncSession):
    """handle_webhook with empty STRIPE_WEBHOOK_SECRET → HTTPException 400 (line 187)."""
    from fastapi import HTTPException

    with patch("app.services.billing_service.settings") as ms:
        ms.STRIPE_WEBHOOK_SECRET = ""
        with pytest.raises(HTTPException) as exc:
            await billing_service.handle_webhook(b"test", "t=1,v1=abc", db_session)

    assert exc.value.status_code == 400


async def test_payment_succeeded_no_stripe_sub_id(db_session: AsyncSession):
    """invoice.payment_succeeded with subscription=None → early return, no DB changes (line 261)."""
    event = _make_event("invoice.payment_succeeded", {"subscription": None, "customer": "cus_test"})

    with patch("stripe.Webhook.construct_event", return_value=event), \
         patch("app.services.billing_service._init_stripe"), \
         patch("app.services.billing_service.settings") as ms:
        ms.STRIPE_WEBHOOK_SECRET = "whsec_test"
        ms.STRIPE_SECRET_KEY = "sk_test"
        # Should return without error or DB writes
        await billing_service.handle_webhook(b"payload", "sig", db_session)


async def test_subscription_deleted_no_sub_id(db_session: AsyncSession):
    """customer.subscription.deleted with id=None → early return, no DB changes (line 315)."""
    event = _make_event("customer.subscription.deleted", {"id": None})

    with patch("stripe.Webhook.construct_event", return_value=event), \
         patch("app.services.billing_service._init_stripe"), \
         patch("app.services.billing_service.settings") as ms:
        ms.STRIPE_WEBHOOK_SECRET = "whsec_test"
        ms.STRIPE_SECRET_KEY = "sk_test"
        # Should return without error or DB writes
        await billing_service.handle_webhook(b"payload", "sig", db_session)
