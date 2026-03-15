import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location
from app.models.review import Review


@pytest.fixture
async def location(db_session: AsyncSession, test_user):
    loc = Location(
        id=uuid.uuid4(),
        user_id=test_user.id,
        gmb_location_id="accounts/123/locations/456",
        name="Test Café",
        address="1 Rue de la Paix, Paris",
        is_active=True,
    )
    db_session.add(loc)
    await db_session.flush()
    return loc


@pytest.fixture
async def review(db_session: AsyncSession, location):
    rv = Review(
        id=uuid.uuid4(),
        location_id=location.id,
        gmb_review_id="reviews/abc123",
        author_name="Alice",
        rating=5,
        comment="Excellent service!",
        language="en",
        status="pending",
    )
    db_session.add(rv)
    await db_session.flush()
    return rv


@pytest.mark.asyncio
async def test_list_reviews_empty(client: AsyncClient, auth_headers):
    response = await client.get("/reviews/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["reviews"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_reviews_with_data(client: AsyncClient, auth_headers, review):
    response = await client.get("/reviews/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["reviews"][0]["author_name"] == "Alice"
    assert data["reviews"][0]["rating"] == 5


@pytest.mark.asyncio
async def test_list_reviews_filter_by_status(client: AsyncClient, auth_headers, review):
    # pending
    resp = await client.get("/reviews/?status=pending", headers=auth_headers)
    assert resp.json()["total"] == 1

    # responded — should be empty
    resp = await client.get("/reviews/?status=responded", headers=auth_headers)
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_update_review_status(client: AsyncClient, auth_headers, review):
    response = await client.patch(
        f"/reviews/{review.id}/status?status=ignored",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


@pytest.mark.asyncio
async def test_update_review_invalid_status(client: AsyncClient, auth_headers, review):
    response = await client.patch(
        f"/reviews/{review.id}/status?status=unknown",
        headers=auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_review_not_found(client: AsyncClient, auth_headers):
    response = await client.patch(
        f"/reviews/{uuid.uuid4()}/status?status=ignored",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_sync_reviews_no_locations(client: AsyncClient, auth_headers):
    """Sync without any active location returns 404."""
    response = await client.post("/reviews/sync", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_sync_reviews_mocked(client: AsyncClient, auth_headers, location):
    """Sync with a mocked GMB service."""
    with patch("app.routers.reviews.GMBService") as MockGMB:
        instance = MockGMB.return_value
        instance.sync_reviews = AsyncMock(return_value=[])

        response = await client.post("/reviews/sync", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["synced_locations"] == 1
    assert data["new_reviews"] == 0
