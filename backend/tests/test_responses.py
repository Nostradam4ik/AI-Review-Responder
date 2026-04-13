"""Tests for responses router — generate, edit, publish, and auto-publish."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location
from app.models.response import Response
from app.models.review import Review


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def location(db_session: AsyncSession, test_user):
    loc = Location(
        id=uuid.uuid4(),
        user_id=test_user.id,
        gmb_location_id=f"accounts/123/locations/{uuid.uuid4().hex[:8]}",
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
        author_name="Bob",
        rating=4,
        comment="Very good, but could be better.",
        language="en",
        status="pending",
    )
    db_session.add(rv)
    await db_session.flush()
    return rv


def _mock_llm_provider(text: str = "Thank you for your review!"):
    provider = MagicMock()
    provider.MODEL = "test-model"
    provider.generate_response = AsyncMock(return_value=text)
    return provider


# ── generate ──────────────────────────────────────────────────────────────────

async def test_generate_response(client: AsyncClient, auth_headers, review, trial_subscription):
    """Generate AI response — LLM is mocked, returns draft."""
    with patch("app.services.ai_service.get_llm_provider", return_value=_mock_llm_provider("Great draft!")):
        resp = await client.post(
            "/responses/generate",
            json={"review_id": str(review.id), "tone": "warm"},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["ai_draft"] == "Great draft!"
    assert data["tone_used"] == "warm"
    assert data["published_at"] is None
    assert data["model_used"] == "test-model"


async def test_generate_response_not_found(client: AsyncClient, auth_headers, trial_subscription):
    """Generate for unknown review → 404."""
    with patch("app.services.ai_service.get_llm_provider", return_value=_mock_llm_provider()):
        resp = await client.post(
            "/responses/generate",
            json={"review_id": str(uuid.uuid4()), "tone": "formal"},
            headers=auth_headers,
        )
    assert resp.status_code == 404


async def test_generate_response_no_subscription_returns_402(
    client: AsyncClient,
    auth_headers,
    review,
):
    """Generate without any subscription → 402 (access gate)."""
    with patch("app.services.ai_service.get_llm_provider", return_value=_mock_llm_provider()):
        resp = await client.post(
            "/responses/generate",
            json={"review_id": str(review.id), "tone": "warm"},
            headers=auth_headers,
        )
    assert resp.status_code == 402


async def test_generate_uses_provider_model_name(
    client: AsyncClient,
    auth_headers,
    review,
    trial_subscription,
    db_session: AsyncSession,
):
    """model_used is set from provider.MODEL, not a hardcoded string (Bug 5 regression)."""
    mock_provider = MagicMock()
    mock_provider.MODEL = "llama-custom-model"
    mock_provider.generate_response = AsyncMock(return_value="Resp")

    with patch("app.services.ai_service.get_llm_provider", return_value=mock_provider):
        resp = await client.post(
            "/responses/generate",
            json={"review_id": str(review.id), "tone": "warm"},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    assert resp.json()["model_used"] == "llama-custom-model"


# ── edit ──────────────────────────────────────────────────────────────────────

async def test_edit_response(client: AsyncClient, auth_headers, review, trial_subscription):
    """Edit an existing draft — final_text and was_edited are persisted."""
    with patch("app.services.ai_service.get_llm_provider", return_value=_mock_llm_provider("Original")):
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


async def test_edit_response_persisted_to_db(
    client: AsyncClient,
    auth_headers,
    review,
    trial_subscription,
    db_session: AsyncSession,
):
    """Edit response → changes are committed to DB (Bug 3 regression)."""
    with patch("app.services.ai_service.get_llm_provider", return_value=_mock_llm_provider("Draft")):
        gen = await client.post(
            "/responses/generate",
            json={"review_id": str(review.id), "tone": "warm"},
            headers=auth_headers,
        )

    response_id = uuid.UUID(gen.json()["id"])

    await client.put(
        f"/responses/{response_id}",
        json={"final_text": "Human edited"},
        headers=auth_headers,
    )

    # Re-fetch from DB to confirm commit
    result = await db_session.execute(
        select(Response).where(Response.id == response_id)
    )
    saved = result.scalar_one_or_none()
    assert saved is not None
    assert saved.final_text == "Human edited"
    assert saved.was_edited is True


# ── publish ───────────────────────────────────────────────────────────────────

async def test_publish_response(client: AsyncClient, auth_headers, review, trial_subscription):
    """Publish response to GMB — mock get_gmb_service (not GMBService)."""
    with patch("app.services.ai_service.get_llm_provider", return_value=_mock_llm_provider("Thanks!")):
        gen = await client.post(
            "/responses/generate",
            json={"review_id": str(review.id), "tone": "warm"},
            headers=auth_headers,
        )

    response_id = gen.json()["id"]

    mock_gmb = AsyncMock()
    mock_gmb.publish_response = AsyncMock(return_value=True)

    # Patch get_gmb_service in the responses router module
    with patch("app.routers.responses.get_gmb_service", return_value=mock_gmb):
        pub = await client.post(
            f"/responses/{response_id}/publish",
            headers=auth_headers,
        )

    assert pub.status_code == 200
    assert pub.json()["published_at"] is not None


async def test_publish_response_no_google_token(
    client: AsyncClient,
    auth_headers,
    review,
    trial_subscription,
    test_user,
):
    """Publish without Google access token → 400."""
    test_user.access_token = None

    with patch("app.services.ai_service.get_llm_provider", return_value=_mock_llm_provider("Draft")):
        gen = await client.post(
            "/responses/generate",
            json={"review_id": str(review.id), "tone": "warm"},
            headers=auth_headers,
        )

    response_id = gen.json()["id"]

    resp = await client.post(f"/responses/{response_id}/publish", headers=auth_headers)
    assert resp.status_code == 400


async def test_publish_commits_to_db(
    client: AsyncClient,
    auth_headers,
    review,
    trial_subscription,
    db_session: AsyncSession,
):
    """published_at is committed, not just flushed (Bug 1 regression)."""
    with patch("app.services.ai_service.get_llm_provider", return_value=_mock_llm_provider("Thanks!")):
        gen = await client.post(
            "/responses/generate",
            json={"review_id": str(review.id), "tone": "warm"},
            headers=auth_headers,
        )

    response_id = uuid.UUID(gen.json()["id"])

    mock_gmb = AsyncMock()
    mock_gmb.publish_response = AsyncMock(return_value=True)

    with patch("app.routers.responses.get_gmb_service", return_value=mock_gmb):
        await client.post(f"/responses/{response_id}/publish", headers=auth_headers)

    result = await db_session.execute(select(Response).where(Response.id == response_id))
    saved = result.scalar_one_or_none()
    assert saved.published_at is not None

    await db_session.refresh(review)
    assert review.status == "responded"


# ── get_response_for_review ───────────────────────────────────────────────────

async def test_get_response_for_review_none(client: AsyncClient, auth_headers, review, trial_subscription):
    """GET /responses/review/{id} → None when no draft exists."""
    resp = await client.get(f"/responses/review/{review.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() is None


async def test_get_response_for_review_returns_draft(
    client: AsyncClient,
    auth_headers,
    review,
    trial_subscription,
):
    """GET /responses/review/{id} → returns the draft after generation."""
    with patch("app.services.ai_service.get_llm_provider", return_value=_mock_llm_provider("Draft text")):
        await client.post(
            "/responses/generate",
            json={"review_id": str(review.id), "tone": "warm"},
            headers=auth_headers,
        )

    resp = await client.get(f"/responses/review/{review.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["ai_draft"] == "Draft text"


# ── error paths ───────────────────────────────────────────────────────────────

async def test_edit_response_not_found(client: AsyncClient, auth_headers):
    """PUT /responses/{random_id} → 404 when response does not exist."""
    resp = await client.put(
        f"/responses/{uuid.uuid4()}",
        json={"final_text": "updated text"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_publish_response_not_found(client: AsyncClient, auth_headers):
    """POST /responses/{random_id}/publish → 404 when response does not exist."""
    resp = await client.post(
        f"/responses/{uuid.uuid4()}/publish",
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_generate_response_forbidden_other_user(
    client: AsyncClient,
    auth_headers,
    db_session: AsyncSession,
    trial_subscription,
):
    """Generate for a review that belongs to another user → 403 (line 36)."""
    from app.core.security import hash_password
    from app.models.user import User

    user_b = User(
        id=uuid.uuid4(),
        email=f"other-{uuid.uuid4().hex[:8]}@test.com",
        password_hash=hash_password("pass1234"),
        is_active=True,
        email_verified=True,
    )
    db_session.add(user_b)

    location_b = Location(
        id=uuid.uuid4(),
        user_id=user_b.id,
        gmb_location_id=f"accounts/999/locations/{uuid.uuid4().hex[:8]}",
        name="Other Café",
        is_active=True,
    )
    db_session.add(location_b)

    review_b = Review(
        id=uuid.uuid4(),
        location_id=location_b.id,
        gmb_review_id=f"reviews/{uuid.uuid4().hex[:8]}",
        author_name="Eve",
        rating=3,
        comment="Average experience",
        language="en",
        status="pending",
    )
    db_session.add(review_b)
    await db_session.flush()

    with patch("app.services.ai_service.get_llm_provider", return_value=_mock_llm_provider()):
        resp = await client.post(
            "/responses/generate",
            json={"review_id": str(review_b.id), "tone": "professional"},
            headers=auth_headers,
        )

    assert resp.status_code == 403


# ── auto-publish ──────────────────────────────────────────────────────────────

async def test_auto_publish_on_generate_success(
    client: AsyncClient,
    auth_headers,
    db_session: AsyncSession,
    review,
    trial_subscription,
    test_user,
):
    """generate_response with auto_publish=True → draft auto-published to GMB (lines 58–80).

    The client fixture already returns test_user from get_current_user, so
    mutating test_user.auto_publish is sufficient — no extra override needed.
    """
    test_user.auto_publish = True
    await db_session.flush()

    mock_gmb = AsyncMock()
    mock_gmb.publish_response = AsyncMock(return_value=True)

    with patch("app.services.ai_service.get_llm_provider", return_value=_mock_llm_provider("Auto!")), \
         patch("app.routers.responses.get_gmb_service", return_value=mock_gmb):
        resp = await client.post(
            "/responses/generate",
            json={"review_id": str(review.id), "tone": "warm"},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    assert resp.json()["published_at"] is not None


async def test_auto_publish_skipped_on_usage_limit_exceeded(
    client: AsyncClient,
    auth_headers,
    db_session: AsyncSession,
    review,
    trial_subscription,
    test_user,
):
    """auto_publish raises HTTPException (usage limit) → draft returned, publish skipped (lines 81–83)."""
    from fastapi import HTTPException as FastAPIHTTPException

    test_user.auto_publish = True
    await db_session.flush()

    # First call (ai_generate check) passes; second call (ai_publish inside auto_publish) raises
    with patch("app.services.ai_service.get_llm_provider", return_value=_mock_llm_provider("Draft only")), \
         patch(
             "app.routers.responses.check_usage_limit",
             new=AsyncMock(side_effect=[None, FastAPIHTTPException(status_code=429, detail="limit")]),
         ):
        resp = await client.post(
            "/responses/generate",
            json={"review_id": str(review.id), "tone": "warm"},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    assert resp.json()["published_at"] is None
