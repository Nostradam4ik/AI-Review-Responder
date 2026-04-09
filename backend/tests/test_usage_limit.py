"""Tests for check_usage_limit — enforcing trial/plan limits without double-logging."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.usage_limit import check_usage_limit
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

    from unittest.mock import MagicMock as MM
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
