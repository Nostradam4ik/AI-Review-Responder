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
        author_name="Bob",
        rating=4,
        comment="Very good, but could be better.",
        language="en",
        status="pending",
    )
    db_session.add(rv)
    await db_session.flush()
    return rv


@pytest.mark.asyncio
async def test_generate_response(client: AsyncClient, auth_headers, review):
    """Generate AI response — LLM is mocked."""
    with patch("app.services.ai_service.get_llm_provider") as mock_factory:
        mock_provider = AsyncMock()
        mock_provider.generate_response = AsyncMock(return_value="Thank you for your feedback, Bob!")
        mock_factory.return_value = mock_provider

        response = await client.post(
            "/responses/generate",
            json={"review_id": str(review.id), "tone": "warm"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["ai_draft"] == "Thank you for your feedback, Bob!"
    assert data["tone_used"] == "warm"
    assert data["published_at"] is None


@pytest.mark.asyncio
async def test_generate_response_not_found(client: AsyncClient, auth_headers):
    """Generate for unknown review → 404."""
    with patch("app.services.ai_service.get_llm_provider"):
        response = await client.post(
            "/responses/generate",
            json={"review_id": str(uuid.uuid4()), "tone": "formal"},
            headers=auth_headers,
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_edit_response(client: AsyncClient, auth_headers, review):
    """Edit an existing draft."""
    with patch("app.services.ai_service.get_llm_provider") as mock_factory:
        mock_provider = AsyncMock()
        mock_provider.generate_response = AsyncMock(return_value="Original AI draft")
        mock_factory.return_value = mock_provider

        gen = await client.post(
            "/responses/generate",
            json={"review_id": str(review.id), "tone": "warm"},
            headers=auth_headers,
        )

    response_id = gen.json()["id"]

    edit = await client.put(
        f"/responses/{response_id}",
        json={"final_text": "Edited by human"},
        headers=auth_headers,
    )
    assert edit.status_code == 200
    assert edit.json()["final_text"] == "Edited by human"
    assert edit.json()["was_edited"] is True


@pytest.mark.asyncio
async def test_publish_response(client: AsyncClient, auth_headers, review):
    """Publish response to GMB — GMB call is mocked."""
    # First generate
    with patch("app.services.ai_service.get_llm_provider") as mock_factory:
        mock_provider = AsyncMock()
        mock_provider.generate_response = AsyncMock(return_value="Thanks for visiting!")
        mock_factory.return_value = mock_provider

        gen = await client.post(
            "/responses/generate",
            json={"review_id": str(review.id), "tone": "warm"},
            headers=auth_headers,
        )

    response_id = gen.json()["id"]

    # Then publish
    with patch("app.routers.responses.GMBService") as MockGMB:
        instance = MockGMB.return_value
        instance.publish_response = AsyncMock(return_value=True)

        publish = await client.post(
            f"/responses/{response_id}/publish",
            headers=auth_headers,
        )

    assert publish.status_code == 200
    assert publish.json()["published_at"] is not None


@pytest.mark.asyncio
async def test_get_response_for_review(client: AsyncClient, auth_headers, review):
    """GET /responses/review/{id} returns None when no draft exists."""
    response = await client.get(
        f"/responses/review/{review.id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() is None
