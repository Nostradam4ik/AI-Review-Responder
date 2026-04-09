"""Tests for admin router — user management, plan editing, and search escaping."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.models.user import User


# ── Non-admin access ──────────────────────────────────────────────────────────

async def test_non_admin_stats_returns_403(client: AsyncClient, auth_headers):
    """Regular user hitting admin endpoint → 403."""
    resp = await client.get("/admin/stats", headers=auth_headers)
    assert resp.status_code == 403


async def test_non_admin_list_users_returns_403(client: AsyncClient, auth_headers):
    resp = await client.get("/admin/users", headers=auth_headers)
    assert resp.status_code == 403


async def test_non_admin_edit_user_returns_403(client: AsyncClient, auth_headers, test_user):
    resp = await client.put(
        f"/admin/users/{test_user.id}",
        json={"plan": "pro"},
        headers=auth_headers,
    )
    assert resp.status_code == 403


# ── Admin stats ───────────────────────────────────────────────────────────────

async def test_admin_stats_returns_kpis(admin_client: AsyncClient, admin_auth_headers):
    resp = await admin_client.get("/admin/stats", headers=admin_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    for key in ("total_users", "active_subscriptions", "trial_users", "mrr"):
        assert key in data


# ── Admin list users ──────────────────────────────────────────────────────────

async def test_admin_list_users(
    admin_client: AsyncClient,
    admin_auth_headers,
    db_session: AsyncSession,
    test_user: User,
):
    resp = await admin_client.get("/admin/users", headers=admin_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "users" in data
    assert "total" in data


async def test_admin_list_users_search_percent_no_crash(
    admin_client: AsyncClient,
    admin_auth_headers,
):
    """search=% should not crash or return wrong results (Bug 11 regression)."""
    resp = await admin_client.get("/admin/users?search=%", headers=admin_auth_headers)
    assert resp.status_code == 200


async def test_admin_list_users_search_underscore_no_crash(
    admin_client: AsyncClient,
    admin_auth_headers,
):
    """search=_ should not crash or return wrong results (Bug 11 regression)."""
    resp = await admin_client.get("/admin/users?search=_", headers=admin_auth_headers)
    assert resp.status_code == 200


async def test_admin_list_users_search_escaped_correctly(
    admin_client: AsyncClient,
    admin_auth_headers,
    db_session: AsyncSession,
):
    """search=% does NOT match all users (must be escaped to literal %)."""
    resp = await admin_client.get("/admin/users?search=%", headers=admin_auth_headers)
    assert resp.status_code == 200
    # With proper escaping, % matches only emails/names literally containing '%'
    # which is none, so result should be 0
    assert resp.json()["total"] == 0


# ── edit_user ─────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def target_user_with_sub(db_session: AsyncSession) -> tuple[User, Subscription]:
    """A secondary user with an active subscription for admin edit tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"target-{uuid.uuid4().hex[:8]}@test.com",
        business_name="Target Biz",
        email_verified=True,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    sub = Subscription(
        user_id=user.id,
        plan_id="starter",
        status="active",
        current_period_start=datetime.now(timezone.utc) - timedelta(days=5),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=25),
    )
    db_session.add(sub)
    await db_session.flush()

    return user, sub


async def test_edit_user_only_plan_does_not_overwrite_subscription_end(
    admin_client: AsyncClient,
    admin_auth_headers,
    db_session: AsyncSession,
    target_user_with_sub,
):
    """edit_user with only plan provided → subscription_end NOT cleared (Bug 6 regression)."""
    user, sub = target_user_with_sub
    original_end = sub.current_period_end

    resp = await admin_client.put(
        f"/admin/users/{user.id}",
        json={"plan": "pro"},
        headers=admin_auth_headers,
    )

    assert resp.status_code == 200

    await db_session.refresh(sub)
    # subscription_end must NOT have been overwritten to None
    assert sub.current_period_end is not None
    # It should be unchanged
    assert abs((sub.current_period_end - original_end).total_seconds()) < 2


async def test_edit_user_explicit_subscription_end_updates(
    admin_client: AsyncClient,
    admin_auth_headers,
    db_session: AsyncSession,
    target_user_with_sub,
):
    """edit_user with explicit subscription_end → updates current_period_end."""
    user, sub = target_user_with_sub
    new_end = datetime.now(timezone.utc) + timedelta(days=90)

    resp = await admin_client.put(
        f"/admin/users/{user.id}",
        json={"subscription_end": new_end.isoformat()},
        headers=admin_auth_headers,
    )

    assert resp.status_code == 200

    await db_session.refresh(sub)
    assert sub.current_period_end is not None
    diff = abs((sub.current_period_end - new_end).total_seconds())
    assert diff < 5


async def test_edit_user_status_trialing_requires_trial_end(
    admin_client: AsyncClient,
    admin_auth_headers,
    target_user_with_sub,
):
    """edit_user with status=trialing but no trial_end → 400."""
    user, _ = target_user_with_sub

    resp = await admin_client.put(
        f"/admin/users/{user.id}",
        json={"status": "trialing"},
        headers=admin_auth_headers,
    )

    assert resp.status_code == 400


async def test_edit_user_sets_ai_limit_override(
    admin_client: AsyncClient,
    admin_auth_headers,
    db_session: AsyncSession,
    target_user_with_sub,
):
    """edit_user ai_responses_limit=-1 sets unlimited override."""
    user, sub = target_user_with_sub

    resp = await admin_client.put(
        f"/admin/users/{user.id}",
        json={"ai_responses_limit": -1},
        headers=admin_auth_headers,
    )

    assert resp.status_code == 200
    await db_session.refresh(sub)
    assert sub.responses_limit_override == -1


async def test_edit_user_invalid_plan(
    admin_client: AsyncClient,
    admin_auth_headers,
    target_user_with_sub,
):
    user, _ = target_user_with_sub

    resp = await admin_client.put(
        f"/admin/users/{user.id}",
        json={"plan": "ultimate"},
        headers=admin_auth_headers,
    )

    assert resp.status_code == 400


# ── reset_trial ───────────────────────────────────────────────────────────────

async def test_reset_trial(
    admin_client: AsyncClient,
    admin_auth_headers,
    db_session: AsyncSession,
    target_user_with_sub,
):
    user, sub = target_user_with_sub

    resp = await admin_client.post(
        f"/admin/users/{user.id}/reset-trial",
        json={"days": 7},
        headers=admin_auth_headers,
    )

    assert resp.status_code == 200
    assert resp.json()["reset"] is True

    await db_session.refresh(sub)
    assert sub.status == "trialing"
    assert sub.trial_end is not None
    # Should be approximately 7 days from now
    delta = sub.trial_end - datetime.now(timezone.utc)
    assert 6 <= delta.days <= 7


async def test_reset_trial_does_not_clear_stripe_subscription_id(
    admin_client: AsyncClient,
    admin_auth_headers,
    db_session: AsyncSession,
    target_user_with_sub,
):
    """reset_trial must NOT wipe stripe_subscription_id (bug regression)."""
    user, sub = target_user_with_sub
    sub.stripe_subscription_id = "sub_keep_me"
    sub.stripe_customer_id = "cus_keep_me"
    await db_session.flush()

    await admin_client.post(
        f"/admin/users/{user.id}/reset-trial",
        json={"days": 14},
        headers=admin_auth_headers,
    )

    await db_session.refresh(sub)
    assert sub.stripe_subscription_id == "sub_keep_me"
    assert sub.stripe_customer_id == "cus_keep_me"


# ── soft delete ───────────────────────────────────────────────────────────────

async def test_delete_user_soft_deletes(
    admin_client: AsyncClient,
    admin_auth_headers,
    db_session: AsyncSession,
    target_user_with_sub,
):
    user, _ = target_user_with_sub

    resp = await admin_client.delete(
        f"/admin/users/{user.id}",
        headers=admin_auth_headers,
    )

    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    await db_session.refresh(user)
    assert user.is_active is False
    assert "@deleted.com" in user.email


async def test_delete_admin_user_forbidden(
    admin_client: AsyncClient,
    admin_auth_headers,
    admin_user: User,
):
    """Cannot delete an admin account."""
    resp = await admin_client.delete(
        f"/admin/users/{admin_user.id}",
        headers=admin_auth_headers,
    )

    assert resp.status_code == 403
