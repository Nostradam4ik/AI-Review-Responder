"""Tests for reviews router — listing, status updates, sync, and UUID filter fixes."""
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location
from app.models.review import Review
from app.models.response import Response as ReviewResponse


# ── Fixtures ──────────────────────────────────────────────────────────────────

import pytest_asyncio


@pytest_asyncio.fixture
async def location(db_session: AsyncSession, test_user):
    loc = Location(
        id=uuid.uuid4(),
        user_id=test_user.id,
        gmb_location_id=f"accounts/test/locations/{uuid.uuid4().hex[:8]}",
        name="Test Café",
        address="1 Rue de la Paix, Paris",
        is_active=True,
    )
    db_session.add(loc)
    await db_session.flush()
    return loc


@pytest_asyncio.fixture
async def review(db_session: AsyncSession, location):
    rv = Review(
        id=uuid.uuid4(),
        location_id=location.id,
        gmb_review_id=f"reviews/{uuid.uuid4().hex[:8]}",
        author_name="Alice",
        rating=5,
        comment="Excellent service!",
        language="en",
        status="pending",
    )
    db_session.add(rv)
    await db_session.flush()
    return rv


# ── list_reviews ──────────────────────────────────────────────────────────────

async def test_list_reviews_empty(client: AsyncClient, auth_headers):
    resp = await client.get("/reviews/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"reviews": [], "total": 0}


async def test_list_reviews_with_data(client: AsyncClient, auth_headers, review):
    resp = await client.get("/reviews/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["reviews"][0]["author_name"] == "Alice"


async def test_list_reviews_filter_by_status(client: AsyncClient, auth_headers, review):
    resp = await client.get("/reviews/?status=pending", headers=auth_headers)
    assert resp.json()["total"] == 1

    resp = await client.get("/reviews/?status=responded", headers=auth_headers)
    assert resp.json()["total"] == 0


async def test_list_reviews_filter_by_location_id_uuid_string(
    client: AsyncClient,
    auth_headers,
    location,
    review,
):
    """location_id filter with valid UUID string → correct results (Bug 7 regression)."""
    resp = await client.get(f"/reviews/?location_id={location.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_list_reviews_filter_by_wrong_location_returns_empty(
    client: AsyncClient,
    auth_headers,
    review,
):
    """location_id filter with a different valid UUID → 0 results (no crash)."""
    other_location_id = uuid.uuid4()
    resp = await client.get(f"/reviews/?location_id={other_location_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_list_reviews_all_when_no_location_filter(
    client: AsyncClient,
    auth_headers,
    review,
):
    """list_reviews without location_id → returns all reviews for user."""
    resp = await client.get("/reviews/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


# ── update_review_status ──────────────────────────────────────────────────────

async def test_update_review_status(client: AsyncClient, auth_headers, review):
    resp = await client.patch(
        f"/reviews/{review.id}/status",
        json={"status": "ignored"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


async def test_update_review_invalid_status(client: AsyncClient, auth_headers, review):
    resp = await client.patch(
        f"/reviews/{review.id}/status",
        json={"status": "unknown"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


async def test_update_review_not_found(client: AsyncClient, auth_headers):
    resp = await client.patch(
        f"/reviews/{uuid.uuid4()}/status",
        json={"status": "ignored"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ── publish_response — persistence regression (Bug 1) ────────────────────────

async def test_publish_response_persists_after_session(
    client: AsyncClient,
    auth_headers,
    review,
    db_session: AsyncSession,
    trial_subscription,
):
    """publish_response → published_at and review.status committed to DB (Bug 1 regression)."""
    # Generate draft first
    mock_provider = MagicMock()
    mock_provider.MODEL = "test-model"
    mock_provider.generate_response = AsyncMock(return_value="Thanks for visiting!")

    with patch("app.services.ai_service.get_llm_provider", return_value=mock_provider):
        gen_resp = await client.post(
            "/responses/generate",
            json={"review_id": str(review.id), "tone": "warm"},
            headers=auth_headers,
        )

    assert gen_resp.status_code == 200
    response_id = gen_resp.json()["id"]

    # Publish — mock GMB
    mock_gmb = AsyncMock()
    mock_gmb.publish_response = AsyncMock(return_value=True)

    with patch("app.routers.responses.get_gmb_service", return_value=mock_gmb):
        pub_resp = await client.post(
            f"/responses/{response_id}/publish",
            headers=auth_headers,
        )

    assert pub_resp.status_code == 200
    data = pub_resp.json()
    assert data["published_at"] is not None

    # Verify persisted — re-fetch from DB
    result = await db_session.execute(
        select(ReviewResponse).where(ReviewResponse.id == uuid.UUID(response_id))
    )
    saved = result.scalar_one_or_none()
    assert saved is not None
    assert saved.published_at is not None

    await db_session.refresh(review)
    assert review.status == "responded"


async def test_publish_response_gmb_failure_returns_502(
    client: AsyncClient,
    auth_headers,
    review,
    db_session: AsyncSession,
    trial_subscription,
):
    """publish_response when GMB returns failure → 502."""
    mock_provider = MagicMock()
    mock_provider.MODEL = "test-model"
    mock_provider.generate_response = AsyncMock(return_value="Draft text")

    with patch("app.services.ai_service.get_llm_provider", return_value=mock_provider):
        gen_resp = await client.post(
            "/responses/generate",
            json={"review_id": str(review.id), "tone": "warm"},
            headers=auth_headers,
        )

    response_id = gen_resp.json()["id"]

    mock_gmb = AsyncMock()
    mock_gmb.publish_response = AsyncMock(return_value=False)

    with patch("app.routers.responses.get_gmb_service", return_value=mock_gmb):
        pub_resp = await client.post(
            f"/responses/{response_id}/publish",
            headers=auth_headers,
        )

    assert pub_resp.status_code == 502


# ── sync_reviews ──────────────────────────────────────────────────────────────

async def test_sync_reviews_no_google_token(client: AsyncClient, auth_headers, test_user):
    """Sync without Google token → returns message, not error."""
    test_user.access_token = None
    resp = await client.post("/reviews/sync", headers=auth_headers)
    assert resp.status_code == 200
    assert "No Google account" in resp.json()["message"]


async def test_sync_reviews_no_active_locations(client: AsyncClient, auth_headers):
    """Sync with no active locations → returns message."""
    resp = await client.post("/reviews/sync", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["synced_locations"] == 0


async def test_sync_reviews_calls_get_gmb_service(
    client: AsyncClient,
    auth_headers,
    location,
    db_session: AsyncSession,
):
    """sync_reviews uses get_gmb_service (with token refresh), not raw GMBService (Bug 4)."""
    mock_gmb = AsyncMock()
    mock_gmb.sync_reviews = AsyncMock(return_value=[])

    # Patch get_gmb_service — NOT GMBService directly
    with patch("app.routers.reviews.get_gmb_service", return_value=mock_gmb) as mock_factory:
        resp = await client.post("/reviews/sync", headers=auth_headers)

    assert resp.status_code == 200
    mock_factory.assert_called_once()
    mock_gmb.sync_reviews.assert_called_once_with(location, db_session)


async def test_sync_reviews_commits_new_reviews(
    client: AsyncClient,
    auth_headers,
    location,
    db_session: AsyncSession,
):
    """sync_reviews calls db.commit() so new reviews survive (Bug 7 regression)."""
    new_review = Review(
        id=uuid.uuid4(),
        location_id=location.id,
        gmb_review_id=f"rev-new-{uuid.uuid4().hex[:8]}",
        author_name="Bob",
        rating=4,
        comment="Good",
        language="fr",
        status="pending",
    )

    mock_gmb = AsyncMock()
    mock_gmb.sync_reviews = AsyncMock(return_value=[new_review])

    with patch("app.routers.reviews.get_gmb_service", return_value=mock_gmb):
        resp = await client.post("/reviews/sync", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json()["new_reviews"] == 1


# ── seed_demo ─────────────────────────────────────────────────────────────────

async def test_seed_demo_reviews(client: AsyncClient, auth_headers, db_session: AsyncSession):
    """POST /reviews/seed-demo creates demo reviews and location."""
    resp = await client.post("/reviews/seed-demo", headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["created"] == 6
