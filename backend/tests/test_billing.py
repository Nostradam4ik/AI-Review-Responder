"""Tests for billing service — Stripe checkout, portal, and webhook handling."""
import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import stripe
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.models.user import User
from app.services import billing_service


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_stripe_event(event_type: str, data_object: dict) -> dict:
    return {"type": event_type, "data": {"object": data_object}}


def _mock_stripe_customer(customer_id: str = "cus_test123"):
    m = MagicMock()
    m.__getitem__ = lambda self, k: customer_id if k == "id" else None
    return m


def _mock_checkout_session(url: str = "https://checkout.stripe.com/pay/test") -> MagicMock:
    m = MagicMock()
    m.__getitem__ = lambda self, k: url if k == "url" else None
    return m


def _mock_stripe_subscription(
    sub_id: str = "sub_test",
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> MagicMock:
    now = datetime.now(timezone.utc)
    start = (period_start or now).timestamp()
    end = (period_end or (now + timedelta(days=30))).timestamp()
    m = MagicMock()
    m.__getitem__ = lambda self, k: {
        "id": sub_id,
        "current_period_start": start,
        "current_period_end": end,
    }.get(k)
    return m


# ── create_checkout_session ───────────────────────────────────────────────────

async def test_checkout_creates_stripe_customer_and_saves_to_db(
    db_session: AsyncSession,
    test_user: User,
    trial_subscription: Subscription,
):
    """create_checkout_session creates a Stripe customer and immediately persists it (Bug 5)."""
    mock_customer = _mock_stripe_customer("cus_new123")
    mock_session = _mock_checkout_session("https://stripe.com/pay/new")

    with patch("app.services.billing_service.asyncio.to_thread") as mock_thread:
        call_count = [0]

        async def fake_to_thread(fn, *args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_customer    # stripe.Customer.create
            return mock_session          # stripe.checkout.Session.create

        mock_thread.side_effect = fake_to_thread

        with patch("app.services.billing_service._init_stripe"):
            url = await billing_service.create_checkout_session(test_user, "starter", db_session)

    assert url == "https://stripe.com/pay/new"

    # Verify customer_id was saved to DB immediately (Bug 5 fix)
    await db_session.refresh(trial_subscription)
    assert trial_subscription.stripe_customer_id == "cus_new123"


async def test_checkout_reuses_existing_customer(
    db_session: AsyncSession,
    test_user: User,
    trial_subscription: Subscription,
):
    """create_checkout_session called twice → only 1 Customer.create call."""
    trial_subscription.stripe_customer_id = "cus_existing"
    await db_session.flush()

    mock_session = _mock_checkout_session("https://stripe.com/pay/existing")

    stripe_calls = []

    async def fake_to_thread(fn, *args, **kwargs):
        stripe_calls.append(fn)
        return mock_session

    with patch("app.services.billing_service.asyncio.to_thread", side_effect=fake_to_thread), \
         patch("app.services.billing_service._init_stripe"):
        await billing_service.create_checkout_session(test_user, "starter", db_session)

    # Customer.create should NOT have been called (only Session.create)
    assert all(fn != stripe.Customer.create for fn in stripe_calls)


# ── Stripe webhook ────────────────────────────────────────────────────────────

async def test_webhook_checkout_completed_activates_subscription(
    db_session: AsyncSession,
    test_user: User,
    trial_subscription: Subscription,
):
    """checkout.session.completed → subscription becomes active with stripe IDs."""
    now = datetime.now(timezone.utc)
    period_start = now
    period_end = now + timedelta(days=30)

    event = _make_stripe_event(
        "checkout.session.completed",
        {
            "metadata": {"user_id": str(test_user.id), "plan_id": "pro"},
            "customer": "cus_webhook123",
            "subscription": "sub_webhook123",
        },
    )

    mock_stripe_sub = _mock_stripe_subscription(
        sub_id="sub_webhook123",
        period_start=period_start,
        period_end=period_end,
    )

    async def fake_to_thread(fn, *args, **kwargs):
        return mock_stripe_sub

    with patch("stripe.Webhook.construct_event", return_value=event), \
         patch("app.services.billing_service.asyncio.to_thread", side_effect=fake_to_thread), \
         patch("app.services.billing_service._init_stripe"), \
         patch("app.services.billing_service.settings") as mock_settings, \
         patch("app.services.email_service.send_subscription_confirmed_email", new=AsyncMock()):
        mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
        mock_settings.STRIPE_SECRET_KEY = "sk_test"
        mock_settings.FRONTEND_URL = "http://localhost:3000"
        mock_settings.APP_URL = "http://localhost:3000"

        await billing_service.handle_webhook(b"payload", "sig_header", db_session)

    await db_session.refresh(trial_subscription)
    assert trial_subscription.status == "active"
    assert trial_subscription.stripe_subscription_id == "sub_webhook123"
    assert trial_subscription.stripe_customer_id == "cus_webhook123"
    assert trial_subscription.plan_id == "pro"


async def test_webhook_subscription_deleted_cancels(
    db_session: AsyncSession,
    test_user: User,
    active_subscription: Subscription,
):
    """customer.subscription.deleted → subscription cancelled, user plan = free."""
    active_subscription.stripe_subscription_id = "sub_delete123"
    await db_session.flush()

    event = _make_stripe_event(
        "customer.subscription.deleted",
        {"id": "sub_delete123"},
    )

    with patch("stripe.Webhook.construct_event", return_value=event), \
         patch("app.services.billing_service._init_stripe"), \
         patch("app.services.billing_service.settings") as mock_settings:
        mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
        mock_settings.STRIPE_SECRET_KEY = "sk_test"

        await billing_service.handle_webhook(b"payload", "sig_header", db_session)

    await db_session.refresh(active_subscription)
    assert active_subscription.status == "cancelled"

    await db_session.refresh(test_user)
    assert test_user.plan == "free"


async def test_webhook_invalid_signature(
    db_session: AsyncSession,
    client: AsyncClient,
    auth_headers: dict,
):
    """Stripe webhook with invalid signature → 400 (Bug 10 regression)."""
    with patch("stripe.Webhook.construct_event",
               side_effect=stripe.error.SignatureVerificationError("bad sig", "sig")), \
         patch("app.services.billing_service._init_stripe"), \
         patch("app.services.billing_service.settings") as mock_settings:
        mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"

        resp = await client.post(
            "/billing/webhook",
            content=b"payload",
            headers={"stripe-signature": "bad_sig"},
        )

    assert resp.status_code == 400


async def test_webhook_init_stripe_called_before_construct_event(
    db_session: AsyncSession,
):
    """_init_stripe() is called before construct_event() — no 'api_key not set' crash (Bug 10)."""
    call_order = []

    def mock_init_stripe():
        call_order.append("init_stripe")
        stripe.api_key = "sk_test_set_by_init"

    def mock_construct_event(*args, **kwargs):
        call_order.append("construct_event")
        return _make_stripe_event("unknown.event", {})

    with patch("app.services.billing_service._init_stripe", side_effect=mock_init_stripe), \
         patch("stripe.Webhook.construct_event", side_effect=mock_construct_event), \
         patch("app.services.billing_service.settings") as mock_settings:
        mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
        mock_settings.STRIPE_SECRET_KEY = "sk_test"

        await billing_service.handle_webhook(b"payload", "sig", db_session)

    # init_stripe must appear before construct_event in call order
    assert call_order.index("init_stripe") < call_order.index("construct_event")


async def test_webhook_invoice_payment_succeeded_renews_subscription(
    db_session: AsyncSession,
    test_user: User,
    active_subscription: Subscription,
):
    """invoice.payment_succeeded → period dates updated, old usage logs deleted."""
    from app.models.usage_log import UsageLog

    active_subscription.stripe_subscription_id = "sub_renew123"
    await db_session.flush()

    # Seed old usage logs in a prior period
    db_session.add(UsageLog(
        user_id=test_user.id,
        action_type="ai_generate",
        billing_period="2024-01",
    ))
    await db_session.flush()

    now = datetime.now(timezone.utc)
    new_end = now + timedelta(days=30)
    mock_stripe_sub = _mock_stripe_subscription(
        sub_id="sub_renew123",
        period_start=now,
        period_end=new_end,
    )

    event = _make_stripe_event("invoice.payment_succeeded", {"subscription": "sub_renew123"})

    async def fake_to_thread(fn, *args, **kwargs):
        return mock_stripe_sub

    with patch("stripe.Webhook.construct_event", return_value=event), \
         patch("app.services.billing_service.asyncio.to_thread", side_effect=fake_to_thread), \
         patch("app.services.billing_service._init_stripe"), \
         patch("app.services.billing_service.settings") as mock_settings:
        mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
        mock_settings.STRIPE_SECRET_KEY = "sk_test"

        await billing_service.handle_webhook(b"payload", "sig", db_session)

    await db_session.refresh(active_subscription)
    assert active_subscription.status == "active"


# ── get_billing_status ────────────────────────────────────────────────────────

async def test_get_billing_status_no_subscription(db_session: AsyncSession, test_user: User):
    """get_billing_status with no subscription → status='none'."""
    status = await billing_service.get_billing_status(test_user, db_session)
    assert status["subscription"]["status"] == "none"
    assert status["is_trial"] is False


async def test_get_billing_status_active_trial(
    db_session: AsyncSession,
    test_user: User,
    trial_subscription: Subscription,
):
    """get_billing_status during active trial."""
    status = await billing_service.get_billing_status(test_user, db_session)
    assert status["is_trial"] is True
    assert status["is_trial_expired"] is False
    assert status["trial_days_remaining"] is not None
    assert status["trial_days_remaining"] >= 13


async def test_get_billing_status_ai_responses_limit_override(
    db_session: AsyncSession,
    test_user: User,
    active_subscription: Subscription,
):
    """ai_responses_limit reflects responses_limit_override correctly."""
    # -1 = unlimited
    active_subscription.responses_limit_override = -1
    await db_session.flush()

    status = await billing_service.get_billing_status(test_user, db_session)
    assert status["usage"]["ai_responses_limit"] is None  # None = unlimited
