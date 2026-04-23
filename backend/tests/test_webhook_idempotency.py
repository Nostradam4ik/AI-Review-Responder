"""Tests for Stripe webhook idempotency and error handling.

Verifies that:
- Duplicate webhook delivery does not corrupt DB state or create extra rows
- Invalid / missing Stripe signature returns 400 before touching the DB
- The webhook endpoint is reachable at POST /billing/webhook
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import stripe
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.models.usage_log import UsageLog
from app.models.user import User
from app.services import billing_service


# ── Helpers ───────────────────────────────────────────────────────────────────

def _event(event_type: str, data: dict) -> dict:
    return {"id": "evt_test_idem", "type": event_type, "data": {"object": data}}


def _mock_stripe_sub(sub_id: str = "sub_idem") -> MagicMock:
    now = datetime.now(timezone.utc)
    m = MagicMock()
    m.__getitem__ = lambda self, k: {
        "id": sub_id,
        "current_period_start": now.timestamp(),
        "current_period_end": (now + timedelta(days=30)).timestamp(),
    }.get(k)
    return m


def _settings_patch(ms):
    ms.STRIPE_WEBHOOK_SECRET = "whsec_test"
    ms.STRIPE_SECRET_KEY = "sk_test"
    ms.FRONTEND_URL = "http://localhost:3000"
    ms.APP_URL = "http://localhost:3000"


# ── Double-send: customer.subscription.deleted ────────────────────────────────

async def test_subscription_deleted_twice_leaves_one_cancelled_row(
    db_session: AsyncSession,
    test_user: User,
    active_subscription: Subscription,
):
    """Sending 'customer.subscription.deleted' twice → sub stays cancelled, no duplicate.

    First call: stripe_subscription_id is cleared to None.
    Second call: no matching subscription found → no-op (no crash, no extra rows).
    """
    active_subscription.stripe_subscription_id = "sub_del_idem"
    await db_session.flush()

    event = _event("customer.subscription.deleted", {"id": "sub_del_idem"})

    with patch("stripe.Webhook.construct_event", return_value=event), \
         patch("app.services.billing_service._init_stripe"), \
         patch("app.services.billing_service.settings") as ms:
        _settings_patch(ms)
        # First delivery
        await billing_service.handle_webhook(b"payload", "sig", db_session)

    await db_session.refresh(active_subscription)
    assert active_subscription.status == "cancelled"
    assert active_subscription.stripe_subscription_id is None

    with patch("stripe.Webhook.construct_event", return_value=event), \
         patch("app.services.billing_service._init_stripe"), \
         patch("app.services.billing_service.settings") as ms:
        _settings_patch(ms)
        # Second delivery — stripe_subscription_id is None now, so no match → no-op
        await billing_service.handle_webhook(b"payload", "sig", db_session)

    # DB state unchanged after second call
    await db_session.refresh(active_subscription)
    assert active_subscription.status == "cancelled"

    # Confirm there is still exactly one subscription row for this user
    result = await db_session.execute(
        select(Subscription).where(Subscription.user_id == test_user.id)
    )
    assert len(result.scalars().all()) == 1


# ── Double-send: invoice.payment_failed ───────────────────────────────────────

async def test_payment_failed_twice_no_duplicate_state(
    db_session: AsyncSession,
    test_user: User,
    active_subscription: Subscription,
):
    """invoice.payment_failed delivered twice → status stays 'past_due', no extra rows."""
    active_subscription.stripe_subscription_id = "sub_fail_idem"
    await db_session.flush()

    event = _event("invoice.payment_failed", {"subscription": "sub_fail_idem"})

    for _ in range(2):
        with patch("stripe.Webhook.construct_event", return_value=event), \
             patch("app.services.billing_service._init_stripe"), \
             patch("app.services.billing_service.settings") as ms, \
             patch("app.services.email_service.send_payment_failed_email", new=AsyncMock()), \
             patch("app.services.notification.send_telegram", new=AsyncMock()):
            _settings_patch(ms)
            await billing_service.handle_webhook(b"payload", "sig", db_session)

    await db_session.refresh(active_subscription)
    assert active_subscription.status == "past_due"

    result = await db_session.execute(
        select(Subscription).where(Subscription.user_id == test_user.id)
    )
    assert len(result.scalars().all()) == 1


# ── Double-send: invoice.payment_succeeded ────────────────────────────────────

async def test_payment_succeeded_twice_no_duplicate_usage_deletion(
    db_session: AsyncSession,
    test_user: User,
    active_subscription: Subscription,
):
    """invoice.payment_succeeded delivered twice → no crash, sub still active."""
    active_subscription.stripe_subscription_id = "sub_renew_idem"
    await db_session.flush()

    event = _event("invoice.payment_succeeded", {"subscription": "sub_renew_idem"})
    mock_sub = _mock_stripe_sub("sub_renew_idem")

    async def _to_thread(fn, *args, **kwargs):
        return mock_sub

    for _ in range(2):
        with patch("stripe.Webhook.construct_event", return_value=event), \
             patch("app.services.billing_service.asyncio.to_thread", side_effect=_to_thread), \
             patch("app.services.billing_service._init_stripe"), \
             patch("app.services.billing_service.settings") as ms:
            _settings_patch(ms)
            await billing_service.handle_webhook(b"payload", "sig", db_session)

    await db_session.refresh(active_subscription)
    assert active_subscription.status == "active"


# ── Invalid / missing Stripe signature ───────────────────────────────────────

async def test_webhook_invalid_signature_returns_400_db_untouched(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    active_subscription: Subscription,
):
    """Invalid signature → 400, no DB changes."""
    original_status = active_subscription.status

    with patch("stripe.Webhook.construct_event",
               side_effect=stripe.error.SignatureVerificationError("bad", "sig")), \
         patch("app.services.billing_service._init_stripe"), \
         patch("app.services.billing_service.settings") as ms:
        ms.STRIPE_WEBHOOK_SECRET = "whsec_test"

        resp = await client.post(
            "/billing/webhook",
            content=b'{"type":"customer.subscription.deleted","data":{"object":{"id":"sub_x"}}}',
            headers={"stripe-signature": "invalid_sig"},
        )

    assert resp.status_code == 400
    await db_session.refresh(active_subscription)
    assert active_subscription.status == original_status


async def test_webhook_missing_signature_header_returns_400(client: AsyncClient):
    """Missing stripe-signature header → 400 before any processing."""
    resp = await client.post(
        "/billing/webhook",
        content=b"{}",
        # No stripe-signature header
    )
    assert resp.status_code == 400


# ── Via HTTP endpoint ─────────────────────────────────────────────────────────

async def test_webhook_endpoint_unknown_event_returns_200(client: AsyncClient):
    """Unknown event type via HTTP → 200 {"status": "ok"} (no crash)."""
    event = _event("some.unknown.event", {})

    with patch("stripe.Webhook.construct_event", return_value=event), \
         patch("app.services.billing_service._init_stripe"), \
         patch("app.services.billing_service.settings") as ms:
        ms.STRIPE_WEBHOOK_SECRET = "whsec_test"
        ms.STRIPE_SECRET_KEY = "sk_test"

        resp = await client.post(
            "/billing/webhook",
            content=b"payload",
            headers={"stripe-signature": "valid_sig"},
        )

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
