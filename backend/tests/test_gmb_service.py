"""Unit tests for GMBService — token refresh, review sync, timeout configuration."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location
from app.models.review import Review
from app.models.user import User
from app.services.gmb_service import GMBService, get_gmb_service, refresh_google_token


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_review_response(
    review_id: str = "rev_001",
    rating: str = "FIVE",
    comment: str = "Great!",
    language: str = "en",
) -> dict:
    return {
        "reviewId": review_id,
        "starRating": rating,
        "comment": comment,
        "languageCode": language,
        "createTime": "2024-01-15T10:00:00Z",
        "reviewer": {"displayName": "Test User"},
    }


def _gmb_reviews_payload(reviews: list[dict], next_page_token: str | None = None) -> dict:
    payload = {"reviews": reviews}
    if next_page_token:
        payload["nextPageToken"] = next_page_token
    return payload


# ── refresh_google_token ──────────────────────────────────────────────────────

async def test_refresh_token_skipped_when_still_valid(
    db_session: AsyncSession,
    test_user: User,
):
    """Token not refreshed if still valid for > 5 minutes."""
    test_user.token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    test_user.access_token = "still_valid_token"

    with patch("app.services.gmb_service.httpx.AsyncClient") as MockClient:
        await refresh_google_token(test_user, db_session)
        MockClient.assert_not_called()

    assert test_user.access_token == "still_valid_token"


async def test_refresh_token_called_when_expired(
    db_session: AsyncSession,
    test_user: User,
):
    """Token is refreshed when expired."""
    test_user.token_expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    test_user.refresh_token = "refresh_tok"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"access_token": "new_token", "expires_in": 3600}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("app.services.gmb_service.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value = mock_client
        await refresh_google_token(test_user, db_session)

    assert test_user.access_token == "new_token"


async def test_refresh_token_no_refresh_token_raises(
    db_session: AsyncSession,
    test_user: User,
):
    """ValueError raised if user has no refresh_token."""
    test_user.token_expires_at = None
    test_user.refresh_token = None

    with pytest.raises(ValueError, match="No refresh token"):
        await refresh_google_token(test_user, db_session)


# ── get_gmb_service ───────────────────────────────────────────────────────────

async def test_get_gmb_service_returns_gmb_instance(
    db_session: AsyncSession,
    test_user: User,
):
    """get_gmb_service refreshes token and returns a GMBService."""
    test_user.token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    test_user.access_token = "valid_token"

    service = await get_gmb_service(test_user, db_session)
    assert isinstance(service, GMBService)


# ── GMBService.sync_reviews ───────────────────────────────────────────────────

async def test_sync_reviews_saves_new_reviews(db_session: AsyncSession, test_user: User):
    """sync_reviews fetches from GMB and upserts reviews into DB."""
    location = Location(
        id=uuid.uuid4(),
        user_id=test_user.id,
        gmb_location_id="accounts/123/locations/456",
        name="Test Place",
        is_active=True,
    )
    db_session.add(location)
    await db_session.flush()

    reviews_page = _gmb_reviews_payload([
        _mock_review_response("r001", "FIVE", "Excellent!", "fr"),
        _mock_review_response("r002", "THREE", "Okay", "en"),
    ])

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = reviews_page

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("app.services.gmb_service.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value = mock_client
        service = GMBService("fake_token")
        new_reviews = await service.sync_reviews(location, db_session)

    assert len(new_reviews) == 2
    ratings = {r.gmb_review_id: r.rating for r in new_reviews}
    assert ratings["r001"] == 5
    assert ratings["r002"] == 3


async def test_sync_reviews_skips_existing_reviews(db_session: AsyncSession, test_user: User):
    """sync_reviews does not create duplicates for already-saved reviews."""
    location = Location(
        id=uuid.uuid4(),
        user_id=test_user.id,
        gmb_location_id="accounts/123/locations/789",
        name="Test Place",
        is_active=True,
    )
    db_session.add(location)

    existing = Review(
        id=uuid.uuid4(),
        location_id=location.id,
        gmb_review_id="r_existing",
        author_name="Alice",
        rating=4,
        comment="Good",
        status="pending",
    )
    db_session.add(existing)
    await db_session.flush()

    reviews_page = _gmb_reviews_payload([
        _mock_review_response("r_existing", "FOUR", "Good"),
    ])

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = reviews_page

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("app.services.gmb_service.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value = mock_client
        service = GMBService("fake_token")
        new_reviews = await service.sync_reviews(location, db_session)

    assert len(new_reviews) == 0


async def test_sync_reviews_language_field_saved(db_session: AsyncSession, test_user: User):
    """Review language field is saved from GMB API (languageCode)."""
    location = Location(
        id=uuid.uuid4(),
        user_id=test_user.id,
        gmb_location_id="accounts/123/locations/lang_test",
        name="Lang Test",
        is_active=True,
    )
    db_session.add(location)
    await db_session.flush()

    reviews_page = _gmb_reviews_payload([
        _mock_review_response("r_fr", "FOUR", "Très bien", language="fr"),
    ])

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = reviews_page

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("app.services.gmb_service.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value = mock_client
        service = GMBService("fake_token")
        new_reviews = await service.sync_reviews(location, db_session)

    assert new_reviews[0].language == "fr"


async def test_sync_reviews_uses_30s_timeout(db_session: AsyncSession, test_user: User):
    """httpx.AsyncClient is created with timeout=30.0 (Bug 8 regression)."""
    location = Location(
        id=uuid.uuid4(),
        user_id=test_user.id,
        gmb_location_id="accounts/123/locations/timeout_test",
        name="Timeout Test",
        is_active=True,
    )
    db_session.add(location)
    await db_session.flush()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = _gmb_reviews_payload([])

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    client_kwargs = {}

    original_init = httpx.AsyncClient.__init__

    def capture_init(self, *args, **kwargs):
        client_kwargs.update(kwargs)
        return original_init(self, *args, **kwargs)

    with patch("app.services.gmb_service.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value = mock_client
        service = GMBService("fake_token")
        await service.sync_reviews(location, db_session)

        # Check the constructor kwargs when AsyncClient was called
        call_kwargs = MockClient.call_args
        assert call_kwargs is not None
        assert call_kwargs.kwargs.get("timeout") == 30.0 or (
            len(call_kwargs.args) > 0 and call_kwargs.args[0] == 30.0
        ), f"Expected timeout=30.0, got: {call_kwargs}"


async def test_sync_reviews_handles_gmb_api_error_gracefully(
    db_session: AsyncSession,
    test_user: User,
):
    """sync_reviews returns empty list when GMB returns non-200 status."""
    location = Location(
        id=uuid.uuid4(),
        user_id=test_user.id,
        gmb_location_id="accounts/123/locations/error_test",
        name="Error Test",
        is_active=True,
    )
    db_session.add(location)
    await db_session.flush()

    mock_resp = MagicMock()
    mock_resp.status_code = 503  # Service unavailable

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("app.services.gmb_service.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value = mock_client
        service = GMBService("fake_token")
        new_reviews = await service.sync_reviews(location, db_session)

    assert new_reviews == []


# ── GMBService.publish_response ───────────────────────────────────────────────

async def test_publish_response_success():
    """publish_response returns True on 200/201."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    mock_client = AsyncMock()
    mock_client.put = AsyncMock(return_value=mock_resp)

    with patch("app.services.gmb_service.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value = mock_client
        service = GMBService("fake_token")
        result = await service.publish_response(
            "accounts/1/locations/2", "rev_abc", "Thank you!"
        )

    assert result is True


async def test_publish_response_failure():
    """publish_response returns False on non-200/201."""
    mock_resp = MagicMock()
    mock_resp.status_code = 403

    mock_client = AsyncMock()
    mock_client.put = AsyncMock(return_value=mock_resp)

    with patch("app.services.gmb_service.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value = mock_client
        service = GMBService("fake_token")
        result = await service.publish_response(
            "accounts/1/locations/2", "rev_abc", "Thank you!"
        )

    assert result is False
