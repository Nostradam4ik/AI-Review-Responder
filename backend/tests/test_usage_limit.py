"""Tests for check_usage_limit — enforcing trial/plan limits without double-logging."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.usage_limit import check_usage_limit, get_user_plan_features
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.usage_log import UsageLog
from app.models.user import User


# ── No subscription ───────────────────────────────────────────────────────────

async def test_no_subscription_raises_402(db_session: AsyncSession, test_user: User):
    """User with no subscription → 402 no_subscription."""
    with pytest.raises(HTTPException) as exc_info:
        await check_usage_limit(test_user, "ai_generate", db_session)

    assert exc_info.value.status_code == 402


# ── Trial user ────────────────────────────────────────────────────────────────

async def test_trial_user_does_not_write_usage_log(
    db_session: AsyncSession,
    test_user: User,
    trial_subscription: Subscription,
):
    """check_usage_limit on trial user returns without writing UsageLog (Bug 4 regression).

    ai_service.py is responsible for writing the log — check_usage_limit must NOT
    write a second one, or the usage counter will double-count.
    """
    await check_usage_limit(test_user, "ai_generate", db_session)

    result = await db_session.execute(
        select(UsageLog).where(
            UsageLog.user_id == test_user.id,
            UsageLog.action_type == "ai_generate",
        )
    )
    logs = result.scalars().all()
    assert len(logs) == 0, "check_usage_limit must NOT write UsageLog for trial users"


async def test_expired_trial_raises_402(
    db_session: AsyncSession,
    test_user: User,
    expired_trial_subscription: Subscription,
):
    """Trial that ended → 402 trial_expired."""
    with pytest.raises(HTTPException) as exc_info:
        await check_usage_limit(test_user, "ai_generate", db_session)

    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["error"] == "trial_expired"


async def test_trial_null_trial_end_raises_402(
    db_session: AsyncSession,
    test_user: User,
):
    """Trial subscription with NULL trial_end is treated as expired (Bug 4 related)."""
    sub = Subscription(
        user_id=test_user.id,
        plan_id="starter",
        status="trialing",
        trial_end=None,
    )
    db_session.add(sub)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        await check_usage_limit(test_user, "ai_generate", db_session)

    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["error"] == "trial_expired"


# ── Active paid subscription ───────────────────────────────────────────────────

async def test_active_subscription_within_limit_writes_log(
    db_session: AsyncSession,
    test_user: User,
    active_subscription: Subscription,
):
    """Active sub within limit → UsageLog written once."""
    await check_usage_limit(test_user, "ai_generate", db_session)

    result = await db_session.execute(
        select(UsageLog).where(
            UsageLog.user_id == test_user.id,
            UsageLog.action_type == "ai_generate",
        )
    )
    logs = result.scalars().all()
    assert len(logs) == 1


async def test_active_subscription_at_monthly_limit_raises_429(
    db_session: AsyncSession,
    test_user: User,
):
    """Active sub with starter plan (100 limit) → 429 after limit reached."""
    sub = Subscription(
        user_id=test_user.id,
        plan_id="starter",
        status="active",
        current_period_end=datetime.now(timezone.utc) + timedelta(days=25),
    )
    db_session.add(sub)
    await db_session.flush()

    # Fill the monthly quota
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    for _ in range(100):
        db_session.add(UsageLog(
            user_id=test_user.id,
            action_type="ai_generate",
            billing_period=period,
        ))
    await db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        await check_usage_limit(test_user, "ai_generate", db_session)

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["error"] == "monthly_limit_reached"


async def test_pro_subscription_no_limit_enforced(
    db_session: AsyncSession,
    test_user: User,
    pro_subscription: Subscription,
):
    """Pro plan (max_responses=0 = unlimited) → no 429 regardless of usage."""
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    # Simulate heavy usage
    for _ in range(500):
        db_session.add(UsageLog(
            user_id=test_user.id,
            action_type="ai_generate",
            billing_period=period,
        ))
    await db_session.flush()

    # Should NOT raise
    await check_usage_limit(test_user, "ai_generate", db_session)


async def test_admin_override_unlimited(
    db_session: AsyncSession,
    test_user: User,
    active_subscription: Subscription,
):
    """responses_limit_override=-1 disables monthly limit entirely."""
    active_subscription.responses_limit_override = -1
    await db_session.flush()

    period = datetime.now(timezone.utc).strftime("%Y-%m")
    for _ in range(200):
        db_session.add(UsageLog(
            user_id=test_user.id,
            action_type="ai_generate",
            billing_period=period,
        ))
    await db_session.flush()

    # Should NOT raise — override=-1 means unlimited
    await check_usage_limit(test_user, "ai_generate", db_session)


async def test_admin_override_custom_cap(
    db_session: AsyncSession,
    test_user: User,
    active_subscription: Subscription,
):
    """responses_limit_override=5 caps at 5 regardless of plan default (100)."""
    active_subscription.responses_limit_override = 5
    await db_session.flush()

    period = datetime.now(timezone.utc).strftime("%Y-%m")
    for _ in range(5):
        db_session.add(UsageLog(
            user_id=test_user.id,
            action_type="ai_generate",
            billing_period=period,
        ))
    await db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        await check_usage_limit(test_user, "ai_generate", db_session)

    assert exc_info.value.status_code == 429


async def test_expired_active_subscription_raises_402(
    db_session: AsyncSession,
    test_user: User,
):
    """Active sub with current_period_end in the past → 402 subscription_expired."""
    sub = Subscription(
        user_id=test_user.id,
        plan_id="starter",
        status="active",
        current_period_end=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(sub)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        await check_usage_limit(test_user, "ai_generate", db_session)

    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["error"] == "subscription_expired"


# ── AI generation usage count integrity ──────────────────────────────────────

async def test_single_ai_generation_creates_exactly_one_usage_log(
    db_session: AsyncSession,
    test_user: User,
    trial_subscription: Subscription,
):
    """Calling generate endpoint → exactly 1 UsageLog entry, not 2 (Bug 4 regression).

    check_usage_limit does NOT log for trial users.
    ai_service.generate_and_save writes the log once.
    Total must be exactly 1.
    """
    from app.models.location import Location
    from app.models.review import Review

    location = Location(
        id=uuid.uuid4(),
        user_id=test_user.id,
        gmb_location_id=f"loc-{uuid.uuid4().hex[:8]}",
        name="Test Loc",
        is_active=True,
    )
    db_session.add(location)

    review = Review(
        id=uuid.uuid4(),
        location_id=location.id,
        gmb_review_id=f"rev-{uuid.uuid4().hex[:8]}",
        author_name="Claude",
        rating=5,
        comment="Amazing!",
        language="en",
        status="pending",
    )
    db_session.add(review)
    await db_session.flush()

    mock_provider = MagicMock()
    mock_provider.MODEL = "test-model"
    mock_provider.generate_response = AsyncMock(return_value="Great response!")

    with patch("app.services.ai_service.get_llm_provider", return_value=mock_provider):
        from app.services.ai_service import generate_and_save
        await generate_and_save(review.id, db_session, tone="warm")

    result = await db_session.execute(
        select(UsageLog).where(
            UsageLog.user_id == test_user.id,
            UsageLog.action_type == "ai_generate",
        )
    )
    logs = result.scalars().all()
    assert len(logs) == 1, f"Expected exactly 1 UsageLog, got {len(logs)}"


# ── Feature gates ─────────────────────────────────────────────────────────────

async def test_feature_gate_auto_respond_blocked_on_starter(
    db_session: AsyncSession,
    test_user: User,
    active_subscription: Subscription,
):
    """Starter plan has auto_respond=False → check_usage_limit raises 403."""
    with pytest.raises(HTTPException) as exc_info:
        await check_usage_limit(test_user, "auto_respond", db_session)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error"] == "feature_not_available"
    assert exc_info.value.detail["feature"] == "auto_respond"


async def test_feature_gate_export_csv_blocked_on_starter(
    db_session: AsyncSession,
    test_user: User,
    active_subscription: Subscription,
):
    """Starter plan has export_csv=False → check_usage_limit raises 403."""
    with pytest.raises(HTTPException) as exc_info:
        await check_usage_limit(test_user, "export_csv", db_session)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["feature"] == "export_csv"


async def test_feature_gate_export_csv_allowed_on_pro(
    db_session: AsyncSession,
    test_user: User,
    pro_subscription: Subscription,
):
    """Pro plan has export_csv=True → check_usage_limit does NOT raise."""
    # Should not raise
    await check_usage_limit(test_user, "export_csv", db_session)


async def test_feature_gate_analytics_blocked_on_starter(
    db_session: AsyncSession,
    test_user: User,
    active_subscription: Subscription,
):
    """Starter plan has analytics=False → check_usage_limit raises 403."""
    with pytest.raises(HTTPException) as exc_info:
        await check_usage_limit(test_user, "analytics", db_session)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["feature"] == "analytics"


async def test_feature_gate_analytics_allowed_on_pro(
    db_session: AsyncSession,
    test_user: User,
    pro_subscription: Subscription,
):
    """Pro plan has analytics=True → check_usage_limit does NOT raise."""
    await check_usage_limit(test_user, "analytics", db_session)


# ── Month boundary with freezegun ─────────────────────────────────────────────

async def test_usage_rolls_over_at_month_boundary(
    db_session: AsyncSession,
    test_user: User,
):
    """Usage from last month is NOT counted toward the current month's limit."""
    from freezegun import freeze_time

    sub = Subscription(
        user_id=test_user.id,
        plan_id="starter",
        status="active",
        current_period_end=datetime.now(timezone.utc) + timedelta(days=25),
    )
    db_session.add(sub)

    # Seed 100 logs in March 2026 (filling the limit)
    for _ in range(100):
        db_session.add(UsageLog(
            user_id=test_user.id,
            action_type="ai_generate",
            billing_period="2026-03",
        ))
    await db_session.flush()

    # It is now April — previous month's logs must NOT count
    with freeze_time("2026-04-01 10:00:00"):
        # Should NOT raise — April has 0 logs, limit is 100
        await check_usage_limit(test_user, "ai_generate", db_session)


# ── Non-active subscription statuses ─────────────────────────────────────────

async def test_check_usage_cancelled_subscription(
    db_session: AsyncSession,
    test_user: User,
):
    """Cancelled subscription → 402 subscription_required (line 56 branch)."""
    sub = Subscription(
        user_id=test_user.id,
        plan_id="starter",
        status="cancelled",
    )
    db_session.add(sub)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        await check_usage_limit(test_user, "ai_generate", db_session)

    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["error"] == "subscription_required"


# ── get_user_plan_features ────────────────────────────────────────────────────

async def test_get_user_plan_features_no_subscription(
    db_session: AsyncSession,
    test_user: User,
):
    """No subscription → get_user_plan_features returns empty dict (lines 143–145)."""
    result = await get_user_plan_features(test_user, db_session)
    assert result == {}


async def test_get_user_plan_features_pro_subscription(
    db_session: AsyncSession,
    test_user: User,
    pro_subscription: Subscription,
):
    """Pro subscription → get_user_plan_features returns pro feature flags (lines 146–148)."""
    result = await get_user_plan_features(test_user, db_session)
    assert result.get("auto_respond") is True
    assert result.get("export_csv") is True
    assert result.get("analytics") is True


async def test_usage_limit_enforced_within_same_month(
    db_session: AsyncSession,
    test_user: User,
):
    """100 logs in current month on starter plan → 101st call raises 429."""
    from freezegun import freeze_time

    sub = Subscription(
        user_id=test_user.id,
        plan_id="starter",
        status="active",
        current_period_end=datetime.now(timezone.utc) + timedelta(days=25),
    )
    db_session.add(sub)

    with freeze_time("2026-04-15 12:00:00"):
        period = "2026-04"
        for _ in range(100):
            db_session.add(UsageLog(
                user_id=test_user.id,
                action_type="ai_generate",
                billing_period=period,
            ))
        await db_session.flush()

        with pytest.raises(HTTPException) as exc_info:
            await check_usage_limit(test_user, "ai_generate", db_session)

        assert exc_info.value.status_code == 429
        assert exc_info.value.detail["used"] == 100
