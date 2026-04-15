"""Tests for analytics.py: overview endpoint, intelligence report preview/download, cache, daily limits.

Auth/feature-gate tests use the HTTP client (the only way to exercise route-level dependencies).
All logic tests call the route handlers and helpers directly — this ensures coverage.py traces
the async function bodies, which ASGI transport dispatch does not.
"""
import json
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.main import app
from app.models.analytics_cache import AnalyticsCache
from app.models.location import Location
from app.models.review import Review
from app.models.subscription import Subscription
from app.models.user import User


# ── Constants ─────────────────────────────────────────────────────────────────

MOCK_ANALYSIS = {
    "business_type": "restaurant",
    "overall_sentiment": "positive",
    "avg_rating": 4.5,
    "nps_estimate": 50,
    "summary": "Good performance overall.",
    "complaints": [],
    "praises": [{"theme": "Service", "frequency": 5, "example": "Great staff"}],
    "urgent_alerts": [],
    "opportunities": [],
    "comparison": {"vs_previous_period": "No change", "response_rate": "50%"},
    "action_plan": [],
}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def make_location(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str = "Test Loc",
) -> Location:
    loc = Location(
        id=uuid.uuid4(),
        user_id=user_id,
        gmb_location_id=f"locations/{uuid.uuid4().hex[:16]}",
        name=name,
        is_active=True,
    )
    db.add(loc)
    await db.flush()
    return loc


async def make_review(
    db: AsyncSession,
    location_id: uuid.UUID,
    rating: int,
    comment: str = "Test comment",
    review_date: datetime | None = None,
) -> Review:
    if review_date is None:
        review_date = datetime.now(timezone.utc)
    r = Review(
        id=uuid.uuid4(),
        location_id=location_id,
        gmb_review_id=f"reviews/{uuid.uuid4().hex[:16]}",
        author_name="Test Author",
        rating=rating,
        comment=comment,
        review_date=review_date,
        status="pending",
    )
    db.add(r)
    await db.flush()
    return r


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def location(db_session: AsyncSession, test_user: User) -> Location:
    return await make_location(db_session, test_user.id)


@pytest_asyncio.fixture
async def agency_user(db_session: AsyncSession) -> User:
    from app.core.security import hash_password
    user = User(
        id=uuid.uuid4(),
        email=f"agency-{uuid.uuid4().hex[:8]}@test.com",
        business_name="Agency Business",
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


# ── PART A: GET /analytics overview — HTTP layer (auth/feature gate) ──────────

async def test_analytics_no_auth(raw_client: AsyncClient):
    """No Authorization header → 403 (HTTPBearer)."""
    resp = await raw_client.get("/analytics")
    assert resp.status_code == 403


async def test_analytics_starter_blocked(
    client: AsyncClient,
    active_subscription: Subscription,
):
    """Starter plan has analytics=False → 402 feature_not_available."""
    resp = await client.get("/analytics")
    assert resp.status_code == 402


# ── PART A cont.: GET /analytics overview — direct calls (logic/coverage) ────

async def test_analytics_no_locations_returns_zeros(
    db_session: AsyncSession,
    test_user: User,
    pro_subscription: Subscription,
):
    """Pro user with no locations → zero-valued dict."""
    from app.routers.analytics import get_analytics

    result = await get_analytics(current_user=test_user, db=db_session)

    assert result["total_reviews"] == 0
    assert result["average_rating"] is None
    assert result["response_rate"] == 0.0
    assert result["pending_reviews"] == 0
    assert result["rating_distribution"] == {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}


async def test_analytics_with_reviews_basic(
    db_session: AsyncSession,
    test_user: User,
    pro_subscription: Subscription,
    location: Location,
):
    """Pro user with 3 reviews → correct totals and rating distribution."""
    from app.routers.analytics import get_analytics

    await make_review(db_session, location.id, rating=5, comment="Excellent!")
    await make_review(db_session, location.id, rating=4, comment="Very good")
    await make_review(db_session, location.id, rating=3, comment="OK")

    result = await get_analytics(current_user=test_user, db=db_session)

    assert result["total_reviews"] == 3
    assert result["average_rating"] is not None
    assert result["pending_reviews"] == 3
    assert result["rating_distribution"]["5"] == 1
    assert result["rating_distribution"]["4"] == 1
    assert result["rating_distribution"]["3"] == 1


async def test_analytics_reviews_last_7_days_count(
    db_session: AsyncSession,
    test_user: User,
    pro_subscription: Subscription,
    location: Location,
):
    """reviews_last_7_days counts only reviews within the past 7 days."""
    from app.routers.analytics import get_analytics

    now = datetime.now(timezone.utc)
    await make_review(db_session, location.id, rating=5, review_date=now - timedelta(days=3))
    await make_review(db_session, location.id, rating=4, review_date=now - timedelta(days=6))
    await make_review(db_session, location.id, rating=3, review_date=now - timedelta(days=10))

    result = await get_analytics(current_user=test_user, db=db_session)

    assert result["reviews_last_7_days"] == 2
    assert result["total_reviews"] == 3


async def test_analytics_reviews_last_30_days_count(
    db_session: AsyncSession,
    test_user: User,
    pro_subscription: Subscription,
    location: Location,
):
    """reviews_last_30_days counts only reviews within the past 30 days."""
    from app.routers.analytics import get_analytics

    now = datetime.now(timezone.utc)
    await make_review(db_session, location.id, rating=5, review_date=now - timedelta(days=5))
    await make_review(db_session, location.id, rating=4, review_date=now - timedelta(days=25))
    await make_review(db_session, location.id, rating=3, review_date=now - timedelta(days=35))

    result = await get_analytics(current_user=test_user, db=db_session)

    assert result["reviews_last_30_days"] == 2
    assert result["total_reviews"] == 3


async def test_analytics_only_own_locations(
    db_session: AsyncSession,
    test_user: User,
    pro_subscription: Subscription,
    location: Location,
):
    """Reviews from another user's location are not counted."""
    from app.core.security import hash_password
    from app.routers.analytics import get_analytics

    other_user = User(
        id=uuid.uuid4(),
        email=f"other-{uuid.uuid4().hex[:8]}@test.com",
        password_hash=hash_password("pass"),
        is_active=True,
        email_verified=True,
    )
    db_session.add(other_user)
    await db_session.flush()

    other_loc = await make_location(db_session, other_user.id, name="Other Loc")
    for _ in range(3):
        await make_review(db_session, other_loc.id, rating=5)

    await make_review(db_session, location.id, rating=4)

    result = await get_analytics(current_user=test_user, db=db_session)

    assert result["total_reviews"] == 1


# ── PART B: GET /analytics/report/preview — HTTP layer (auth/feature gate) ───

async def test_preview_no_auth(raw_client: AsyncClient):
    """No Authorization header → 403."""
    resp = await raw_client.get("/analytics/report/preview")
    assert resp.status_code == 403


async def test_preview_starter_blocked(
    client: AsyncClient,
    active_subscription: Subscription,
):
    """Starter plan → 402 feature_not_available."""
    resp = await client.get("/analytics/report/preview")
    assert resp.status_code == 402


# ── PART B cont.: preview — direct calls (logic/coverage) ────────────────────

async def test_preview_pro_no_location(
    db_session: AsyncSession,
    test_user: User,
    pro_subscription: Subscription,
):
    """Pro user with no locations → fallback summary; LLM not called."""
    from app.routers.analytics import preview_intelligence_report

    with patch(
        "app.services.review_intelligence.generate_intelligence_report",
        new_callable=AsyncMock,
        return_value=MOCK_ANALYSIS,
    ) as mock_llm:
        response = await preview_intelligence_report(
            location_id=None,
            period="month",
            current_user=test_user,
            db=db_session,
        )

    data = json.loads(response.body)
    assert "No locations found" in data["analysis"]["summary"]
    mock_llm.assert_not_called()


async def test_preview_pro_with_reviews(
    db_session: AsyncSession,
    test_user: User,
    pro_subscription: Subscription,
    location: Location,
):
    """Pro user with reviews → LLM called once, analysis and meta returned."""
    from app.routers.analytics import preview_intelligence_report

    await make_review(db_session, location.id, rating=5, comment="Amazing!")
    await make_review(db_session, location.id, rating=4, comment="Good place")

    with patch(
        "app.services.review_intelligence.generate_intelligence_report",
        new_callable=AsyncMock,
        return_value=MOCK_ANALYSIS,
    ) as mock_llm:
        response = await preview_intelligence_report(
            location_id=None,
            period="month",
            current_user=test_user,
            db=db_session,
        )

    mock_llm.assert_called_once()
    data = json.loads(response.body)
    assert data["analysis"]["summary"] == MOCK_ANALYSIS["summary"]
    assert "meta" in data
    assert data["meta"]["business_name"] == test_user.business_name


async def test_preview_cache_hit(
    db_session: AsyncSession,
    test_user: User,
    pro_subscription: Subscription,
):
    """Fresh cache entry → LLM not called; cached result served."""
    from app.routers.analytics import preview_intelligence_report

    now = datetime.now(timezone.utc)
    cached_result = {**MOCK_ANALYSIS, "summary": "Cached summary"}
    db_session.add(AnalyticsCache(
        user_id=test_user.id,
        location_id=None,
        period="month",
        cache_date=date.today(),
        result=cached_result,
        expires_at=now + timedelta(hours=5),
        was_cache_hit=False,
    ))
    await db_session.flush()

    with patch(
        "app.services.review_intelligence.generate_intelligence_report",
        new_callable=AsyncMock,
        return_value=MOCK_ANALYSIS,
    ) as mock_llm:
        response = await preview_intelligence_report(
            location_id=None,
            period="month",
            current_user=test_user,
            db=db_session,
        )

    data = json.loads(response.body)
    assert data["analysis"]["summary"] == "Cached summary"
    mock_llm.assert_not_called()


async def test_preview_expired_cache_triggers_llm(
    db_session: AsyncSession,
    test_user: User,
    pro_subscription: Subscription,
    location: Location,
):
    """Expired cache entry → LLM called for a fresh result."""
    from app.routers.analytics import preview_intelligence_report

    now = datetime.now(timezone.utc)
    db_session.add(AnalyticsCache(
        user_id=test_user.id,
        location_id=None,
        period="month",
        cache_date=date.today(),
        result={"summary": "Old stale result"},
        expires_at=now - timedelta(hours=1),
        was_cache_hit=False,
    ))
    await db_session.flush()

    await make_review(db_session, location.id, rating=5, comment="Great!")

    with patch(
        "app.services.review_intelligence.generate_intelligence_report",
        new_callable=AsyncMock,
        return_value=MOCK_ANALYSIS,
    ) as mock_llm:
        response = await preview_intelligence_report(
            location_id=None,
            period="month",
            current_user=test_user,
            db=db_session,
        )

    mock_llm.assert_called_once()
    data = json.loads(response.body)
    assert data["analysis"]["summary"] == MOCK_ANALYSIS["summary"]


async def test_preview_daily_limit_exceeded(
    db_session: AsyncSession,
    test_user: User,
    pro_subscription: Subscription,
):
    """PRO plan: 4 real LLM calls already today → 5th request blocked with 429."""
    from app.routers.analytics import preview_intelligence_report

    now = datetime.now(timezone.utc)
    today = date.today()
    for _ in range(4):
        db_session.add(AnalyticsCache(
            user_id=test_user.id,
            location_id=None,
            period="month",
            cache_date=today,
            result={"summary": "old"},
            expires_at=now - timedelta(hours=1),  # expired — not a cache hit, but counted
            was_cache_hit=False,
        ))
    await db_session.flush()

    with pytest.raises(HTTPException) as exc:
        await preview_intelligence_report(
            location_id=None,
            period="month",
            current_user=test_user,
            db=db_session,
        )

    assert exc.value.status_code == 429
    assert exc.value.detail["error"] == "daily_report_limit_reached"
    assert exc.value.detail["used"] == 4
    assert exc.value.detail["limit"] == 4


async def test_preview_agency_under_daily_limit(
    db_session: AsyncSession,
    agency_user: User,
    agency_subscription: Subscription,
):
    """Agency plan: 7 expired calls today (limit=8) → 8th call succeeds."""
    from app.routers.analytics import preview_intelligence_report

    now = datetime.now(timezone.utc)
    today = date.today()

    loc = await make_location(db_session, agency_user.id)
    await make_review(db_session, loc.id, rating=5, comment="Great service!")

    for _ in range(7):
        db_session.add(AnalyticsCache(
            user_id=agency_user.id,
            location_id=None,
            period="month",
            cache_date=today,
            result={"summary": "old"},
            expires_at=now - timedelta(hours=1),
            was_cache_hit=False,
        ))
    await db_session.flush()

    with patch(
        "app.services.review_intelligence.generate_intelligence_report",
        new_callable=AsyncMock,
        return_value=MOCK_ANALYSIS,
    ):
        response = await preview_intelligence_report(
            location_id=None,
            period="month",
            current_user=agency_user,
            db=db_session,
        )

    data = json.loads(response.body)
    assert "analysis" in data


async def test_preview_location_filter_isolates_reviews(
    db_session: AsyncSession,
    test_user: User,
    pro_subscription: Subscription,
):
    """location_id param restricts which reviews the LLM receives."""
    from app.routers.analytics import preview_intelligence_report

    loc1 = await make_location(db_session, test_user.id, name="Loc 1")
    loc2 = await make_location(db_session, test_user.id, name="Loc 2")

    await make_review(db_session, loc1.id, rating=5, comment="Loc1 review 1")
    await make_review(db_session, loc1.id, rating=4, comment="Loc1 review 2")
    await make_review(db_session, loc2.id, rating=3, comment="Loc2 review only")

    captured_reviews: list = []

    async def capturing_llm(reviews, **kwargs):
        captured_reviews.extend(reviews)
        return MOCK_ANALYSIS

    with patch(
        "app.services.review_intelligence.generate_intelligence_report",
        side_effect=capturing_llm,
    ):
        response = await preview_intelligence_report(
            location_id=loc1.id,
            period="month",
            current_user=test_user,
            db=db_session,
        )

    assert len(captured_reviews) == 2
    assert all(r.location_id == loc1.id for r in captured_reviews)
    assert json.loads(response.body)["analysis"]["summary"] == MOCK_ANALYSIS["summary"]


# ── PART C: GET /analytics/report/download — direct calls ────────────────────

async def test_download_pdf_response(
    db_session: AsyncSession,
    test_user: User,
    pro_subscription: Subscription,
    location: Location,
):
    """format=pdf → application/pdf response with Content-Disposition attachment."""
    from app.routers.analytics import download_intelligence_report

    await make_review(db_session, location.id, rating=5, comment="Perfect!")

    with (
        patch(
            "app.services.review_intelligence.generate_intelligence_report",
            new_callable=AsyncMock,
            return_value=MOCK_ANALYSIS,
        ),
        patch(
            "app.services.pdf_report.generate_pdf_bytes",
            return_value=b"%PDF-1.4 mock",
        ),
    ):
        response = await download_intelligence_report(
            location_id=None,
            period="month",
            format="pdf",
            current_user=test_user,
            db=db_session,
        )

    assert response.body == b"%PDF-1.4 mock"
    assert response.media_type == "application/pdf"
    assert "attachment" in response.headers.get("content-disposition", "")


async def test_download_json_response(
    db_session: AsyncSession,
    test_user: User,
    pro_subscription: Subscription,
    location: Location,
):
    """format=json → JSONResponse containing analysis and meta keys."""
    from app.routers.analytics import download_intelligence_report

    await make_review(db_session, location.id, rating=4, comment="Nice place!")

    with patch(
        "app.services.review_intelligence.generate_intelligence_report",
        new_callable=AsyncMock,
        return_value=MOCK_ANALYSIS,
    ):
        response = await download_intelligence_report(
            location_id=None,
            period="month",
            format="json",
            current_user=test_user,
            db=db_session,
        )

    data = json.loads(response.body)
    assert data["analysis"]["summary"] == MOCK_ANALYSIS["summary"]
    assert "meta" in data


# ── PART D: period=week window ───────────────────────────────────────────────

async def test_preview_period_week_window(
    db_session: AsyncSession,
    test_user: User,
    pro_subscription: Subscription,
    location: Location,
):
    """period=week uses a 7-day window: only reviews within 7 days reach the LLM."""
    from app.routers.analytics import preview_intelligence_report

    now = datetime.now(timezone.utc)
    await make_review(
        db_session, location.id, rating=5,
        comment="Recent review",
        review_date=now - timedelta(days=3),
    )
    await make_review(
        db_session, location.id, rating=3,
        comment="Older review",
        review_date=now - timedelta(days=10),
    )

    with patch(
        "app.services.review_intelligence.generate_intelligence_report",
        new_callable=AsyncMock,
        return_value=MOCK_ANALYSIS,
    ) as mock_llm:
        response = await preview_intelligence_report(
            location_id=None,
            period="week",
            current_user=test_user,
            db=db_session,
        )

    mock_llm.assert_called_once()
    call_reviews = mock_llm.call_args.kwargs["reviews"]
    assert len(call_reviews) == 1
    data = json.loads(response.body)
    assert "week" in data["meta"]["period_label"].lower() or "–" in data["meta"]["period_label"]
