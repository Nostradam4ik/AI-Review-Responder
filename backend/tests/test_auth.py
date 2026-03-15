import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_login_redirects_to_google():
    """GET /auth/login should redirect to Google OAuth."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
    ) as ac:
        response = await ac.get("/auth/login")

    assert response.status_code == 307
    location = response.headers["location"]
    assert "accounts.google.com/o/oauth2/v2/auth" in location
    assert "client_id=" in location
    assert "scope=" in location
    assert "business.manage" in location


@pytest.mark.asyncio
async def test_callback_missing_code():
    """GET /auth/callback without code param returns 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/auth/callback")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_callback_invalid_code():
    """GET /auth/callback with bad code → Google returns error → 400."""
    mock_resp = AsyncMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {"error": "invalid_grant"}

    with patch("app.routers.auth.httpx.AsyncClient") as MockClient:
        instance = MockClient.return_value.__aenter__.return_value
        instance.post = AsyncMock(return_value=mock_resp)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/auth/callback?code=bad_code")

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_me_endpoint_without_token():
    """GET /auth/me is a placeholder that returns 200 with usage hint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/auth/me")
    assert response.status_code == 200
    assert "token" in response.json()["message"].lower()
