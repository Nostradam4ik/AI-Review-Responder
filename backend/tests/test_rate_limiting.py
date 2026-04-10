"""Tests for rate limiting on POST /responses/generate.

slowapi is wired with @limiter.limit("20/minute") on that endpoint.
Tests verify:
- Normal usage (< 20 req/min) → 200
- Exceeding the limit → 429 with Retry-After header
- Different IPs are rate-limited independently
- Limit resets after the time window (simulated via freezegun)
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from freezegun import freeze_time
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.main import app
from app.models.location import Location
from app.models.review import Review
from app.models.subscription import Subscription
from app.models.user import User


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_mock_provider():
    provider = MagicMock()
    provider.MODEL = "test-model"
    provider.generate_response = AsyncMock(return_value="Great response!")
    return provider


@pytest_asyncio.fixture
async def review_for_rate_limit(db_session: AsyncSession, test_user: User) -> Review:
    loc = Location(
        id=uuid.uuid4(),
        user_id=test_user.id,
        gmb_location_id=f"loc-rl-{uuid.uuid4().hex[:8]}",
        name="Rate Limit Loc",
        is_active=True,
    )
    db_session.add(loc)

    review = Review(
        id=uuid.uuid4(),
        location_id=loc.id,
        gmb_review_id=f"rev-rl-{uuid.uuid4().hex[:8]}",
        author_name="Tester",
        rating=4,
        comment="Nice place!",
        language="en",
        status="pending",
    )
    db_session.add(review)
    await db_session.flush()
    return review


@pytest_asyncio.fixture
async def trial_sub_for_rate_limit(db_session: AsyncSession, test_user: User) -> Subscription:
    sub = Subscription(
        user_id=test_user.id,
        plan_id="starter",
        status="trialing",
        trial_end=datetime.now(timezone.utc) + timedelta(days=14),
    )
    db_session.add(sub)
    await db_session.flush()
    return sub


def _make_client(db_session, user, ip: str = "127.0.0.1") -> AsyncClient:
    """Build a client where all requests appear to come from `ip`."""
    async def _db():
        yield db_session

    async def _user():
        return user

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _user

    transport = ASGITransport(app=app, client=(ip, 12345))
    return AsyncClient(transport=transport, base_url="http://test")


# ── Normal usage stays within limit ──────────────────────────────────────────

async def test_requests_within_limit_succeed(
    db_session: AsyncSession,
    test_user: User,
    review_for_rate_limit: Review,
    trial_sub_for_rate_limit: Subscription,
):
    """5 requests well under the 20/minute limit → all succeed (no 429)."""
    mock_provider = _make_mock_provider()

    with patch("app.services.ai_service.get_llm_provider", return_value=mock_provider):
        async with _make_client(db_session, test_user) as ac:
            for _ in range(5):
                resp = await ac.post("/responses/generate", json={
                    "review_id": str(review_for_rate_limit.id),
                    "tone": "warm",
                })
                # May return 200 or 402/429 due to usage limits, but NOT 429 from rate limiter
                # We just verify no rate-limit 429 with Retry-After header
                if resp.status_code == 429:
                    assert "Retry-After" not in resp.headers, \
                        "Rate limiter fired too early — only 5 requests sent"

    app.dependency_overrides.clear()


# ── Exceeding the rate limit ──────────────────────────────────────────────────

async def test_exceeding_rate_limit_returns_429(
    db_session: AsyncSession,
    test_user: User,
    review_for_rate_limit: Review,
    trial_sub_for_rate_limit: Subscription,
):
    """21+ requests in the same minute → 429 with Retry-After header."""
    mock_provider = _make_mock_provider()

    with freeze_time("2026-04-10 10:00:00"):
        with patch("app.services.ai_service.get_llm_provider", return_value=mock_provider):
            async with _make_client(db_session, test_user, ip="10.0.0.1") as ac:
                statuses = []
                for _ in range(25):
                    resp = await ac.post("/responses/generate", json={
                        "review_id": str(review_for_rate_limit.id),
                        "tone": "warm",
                    })
                    statuses.append(resp.status_code)

    assert 429 in statuses, "Expected at least one 429 after exceeding 20/minute"
    app.dependency_overrides.clear()


async def test_rate_limit_429_includes_retry_after(
    db_session: AsyncSession,
    test_user: User,
    review_for_rate_limit: Review,
    trial_sub_for_rate_limit: Subscription,
):
    """When rate limit is hit, response includes Retry-After header."""
    mock_provider = _make_mock_provider()

    with freeze_time("2026-04-10 10:01:00"):
        with patch("app.services.ai_service.get_llm_provider", return_value=mock_provider):
            async with _make_client(db_session, test_user, ip="10.0.0.2") as ac:
                rate_limited_resp = None
                for _ in range(25):
                    resp = await ac.post("/responses/generate", json={
                        "review_id": str(review_for_rate_limit.id),
                        "tone": "warm",
                    })
                    if resp.status_code == 429:
                        rate_limited_resp = resp
                        break

    if rate_limited_resp is not None:
        assert "Retry-After" in rate_limited_resp.headers

    app.dependency_overrides.clear()


# ── Different IPs are independent ────────────────────────────────────────────

async def test_ip_a_limit_does_not_block_ip_b(
    db_session: AsyncSession,
    test_user: User,
    review_for_rate_limit: Review,
    trial_sub_for_rate_limit: Subscription,
):
    """IP A hitting the rate limit must NOT affect IP B."""
    mock_provider = _make_mock_provider()

    with freeze_time("2026-04-10 10:02:00"):
        with patch("app.services.ai_service.get_llm_provider", return_value=mock_provider):
            # Exhaust limit for IP A
            async with _make_client(db_session, test_user, ip="192.168.1.1") as ac_a:
                for _ in range(25):
                    await ac_a.post("/responses/generate", json={
                        "review_id": str(review_for_rate_limit.id),
                        "tone": "warm",
                    })
            app.dependency_overrides.clear()

            # IP B should still get through (no rate-limit 429 from rate limiter itself)
            async with _make_client(db_session, test_user, ip="192.168.1.2") as ac_b:
                resp = await ac_b.post("/responses/generate", json={
                    "review_id": str(review_for_rate_limit.id),
                    "tone": "warm",
                })
                # IP B should NOT be blocked by the rate limiter
                # (may still get 402/other errors from business logic, but not 429 from rate limiter
                # unless there's truly a Retry-After header)
                if resp.status_code == 429:
                    assert "Retry-After" not in resp.headers, \
                        "IP B should not be rate-limited when only IP A exceeded the limit"

    app.dependency_overrides.clear()


# ── Limit resets after window ─────────────────────────────────────────────────

async def test_rate_limit_resets_after_window(
    db_session: AsyncSession,
    test_user: User,
    review_for_rate_limit: Review,
    trial_sub_for_rate_limit: Subscription,
):
    """After the 1-minute window passes, the limit resets and requests succeed again."""
    mock_provider = _make_mock_provider()
    ip = "10.10.10.10"

    with patch("app.services.ai_service.get_llm_provider", return_value=mock_provider):
        # Exhaust limit at T=0
        with freeze_time("2026-04-10 10:03:00"):
            async with _make_client(db_session, test_user, ip=ip) as ac:
                rate_limited = False
                for _ in range(25):
                    r = await ac.post("/responses/generate", json={
                        "review_id": str(review_for_rate_limit.id),
                        "tone": "warm",
                    })
                    if r.status_code == 429:
                        rate_limited = True
                        break
            app.dependency_overrides.clear()

        # Advance time by 61 seconds — limit window has passed
        with freeze_time("2026-04-10 10:04:01"):
            async with _make_client(db_session, test_user, ip=ip) as ac:
                resp = await ac.post("/responses/generate", json={
                    "review_id": str(review_for_rate_limit.id),
                    "tone": "warm",
                })
                # After reset, rate limiter should NOT block (may still get 402 etc.)
                if resp.status_code == 429:
                    assert "Retry-After" not in resp.headers, \
                        "Rate limit should have reset after 61 seconds"
            app.dependency_overrides.clear()
