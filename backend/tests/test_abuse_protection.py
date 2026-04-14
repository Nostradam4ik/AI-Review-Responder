"""Tests for abuse-protection layers: daily report cap, sliding-window rate limit."""
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics_cache import AnalyticsCache
from app.models.subscription import Subscription
from app.models.user import User


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def pro_subscription(db_session: AsyncSession, test_user: User) -> Subscription:
    """Active PRO subscription for test_user (overrides the conftest starter one)."""
    sub = Subscription(
        user_id=test_user.id,
        plan_id="pro",
        status="active",
        current_period_end=datetime.now(timezone.utc) + timedelta(days=25),
    )
    db_session.add(sub)
    await db_session.flush()
    return sub


@pytest_asyncio.fixture
async def agency_user(db_session: AsyncSession) -> User:
    from app.core.security import hash_password
    user = User(
        id=uuid.uuid4(),
        email=f"agency-{uuid.uuid4().hex[:8]}@test.com",
        password_hash=hash_password("pass1234"),
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def agency_subscription(db_session: AsyncSession, agency_user: User) -> Subscription:
    sub = Subscription(
        user_id=agency_user.id,
        plan_id="agency",
        status="active",
        current_period_end=datetime.now(timezone.utc) + timedelta(days=25),
    )
    db_session.add(sub)
    await db_session.flush()
    return sub


# ── PART A: daily report limit ────────────────────────────────────────────────

async def test_daily_report_limit_enforced(
    db_session: AsyncSession,
    test_user: User,
    pro_subscription: Subscription,
):
    """PRO plan allows 4 Intelligence Report LLM calls per day.
    On the 5th call (was_cache_hit=False), check_report_daily_limit must raise 429."""
    from app.core.report_limit import check_report_daily_limit

    today = date.today()
    now = datetime.now(timezone.utc)

    # Insert 4 real LLM calls (was_cache_hit=False) for today
    for _ in range(4):
        db_session.add(AnalyticsCache(
            user_id=test_user.id,
            location_id=None,
            period="month",
            cache_date=today,
            result={"summary": "cached"},
            expires_at=now - timedelta(hours=1),   # expired, but still counts for the daily cap
            was_cache_hit=False,
        ))
    await db_session.flush()

    with pytest.raises(HTTPException) as exc:
        await check_report_daily_limit(test_user, db_session)

    assert exc.value.status_code == 429
    assert exc.value.detail["error"] == "daily_report_limit_reached"
    assert exc.value.detail["used"] == 4
    assert exc.value.detail["limit"] == 4


async def test_cache_hit_bypasses_daily_limit(
    db_session: AsyncSession,
    test_user: User,
    pro_subscription: Subscription,
):
    """When a FRESH cache entry exists, the endpoint serves it without calling
    check_report_daily_limit or the LLM — even if the daily cap is exhausted."""
    from app.routers.analytics import _get_cached_report, _build_report

    today = date.today()
    now = datetime.now(timezone.utc)

    # 4 real LLM calls today (daily cap hit)
    for _ in range(4):
        db_session.add(AnalyticsCache(
            user_id=test_user.id,
            location_id=None,
            period="month",
            cache_date=today,
            result={"summary": "old"},
            expires_at=now - timedelta(hours=1),
            was_cache_hit=False,
        ))

    # Fresh cache entry (not yet expired)
    fresh_result = {"summary": "fresh cached report", "complaints": [], "praises": [],
                    "action_plan": [], "urgent_alerts": [], "opportunities": [],
                    "avg_rating": 4.0, "nps_estimate": 30, "overall_sentiment": "positive",
                    "business_type": "restaurant", "comparison": {}}
    db_session.add(AnalyticsCache(
        user_id=test_user.id,
        location_id=None,
        period="month",
        cache_date=today,
        result=fresh_result,
        expires_at=now + timedelta(hours=5),   # fresh!
        was_cache_hit=False,
    ))
    await db_session.flush()

    # The cache lookup must return the fresh result
    cached = await _get_cached_report(db_session, test_user.id, None, "month")
    assert cached is not None
    assert cached["summary"] == "fresh cached report"

    # _build_report must not call the LLM when cache is fresh
    with patch("app.services.review_intelligence.generate_intelligence_report") as mock_llm:
        analysis, meta = await _build_report(db_session, test_user, None, "month")

    mock_llm.assert_not_called()
    assert analysis["summary"] == "fresh cached report"


# ── PART B: sliding-window rate limit ────────────────────────────────────────

async def test_sliding_window_rate_limit_starter():
    """Starter plan: 10 calls allowed per 60s. 11th call → 429 with Retry-After."""
    from app.routers.responses import _check_sliding_window, _rate_windows

    user_id = f"test-starter-{uuid.uuid4().hex}"
    _rate_windows[user_id] = []  # clean state

    # 10 calls succeed
    for _ in range(10):
        _check_sliding_window(user_id, 10, 60)

    # 11th raises 429
    with pytest.raises(HTTPException) as exc:
        _check_sliding_window(user_id, 10, 60)

    assert exc.value.status_code == 429
    assert exc.value.headers["Retry-After"] == "60"
    assert exc.value.detail["error"] == "rate_limit_exceeded"


async def test_agency_higher_limit():
    """Agency plan: 60 calls allowed per 60s. 61st call → 429."""
    from app.routers.responses import _check_sliding_window, _rate_windows

    user_id = f"test-agency-{uuid.uuid4().hex}"
    _rate_windows[user_id] = []  # clean state

    # 60 calls succeed
    for _ in range(60):
        _check_sliding_window(user_id, 60, 60)

    # 61st raises 429
    with pytest.raises(HTTPException) as exc:
        _check_sliding_window(user_id, 60, 60)

    assert exc.value.status_code == 429
    assert exc.value.detail["error"] == "rate_limit_exceeded"
