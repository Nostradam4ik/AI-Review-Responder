"""Tests for auth endpoints — registration, login, Telegram webhook, OAuth callback."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.user import User


# ── Registration ─────────────────────────────────────────────────────────────

async def test_register_new_user(raw_client: AsyncClient, db_session: AsyncSession):
    """POST /auth/register → 201 and user exists in DB."""
    email = f"newuser-{uuid.uuid4().hex[:8]}@test.com"

    with patch("app.routers.auth.send_welcome_email", new=AsyncMock()):
        resp = await raw_client.post(
            "/auth/register",
            json={"email": email, "password": "securepass1", "business_name": "Biz"},
        )

    assert resp.status_code == 201

    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    assert user is not None
    # email_verified depends on AUTO_VERIFY_EMAIL setting; just check user was created
    assert user.email == email


async def test_register_duplicate_email(raw_client: AsyncClient, db_session: AsyncSession, test_user: User):
    """POST /auth/register with existing email → 409."""
    with patch("app.routers.auth.send_welcome_email", new=AsyncMock()):
        resp = await raw_client.post(
            "/auth/register",
            json={"email": test_user.email, "password": "password123", "business_name": ""},
        )

    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


async def test_register_short_password(raw_client: AsyncClient):
    """POST /auth/register with password < 8 chars → 400."""
    with patch("app.routers.auth.send_welcome_email", new=AsyncMock()):
        resp = await raw_client.post(
            "/auth/register",
            json={"email": "x@test.com", "password": "short", "business_name": ""},
        )

    assert resp.status_code == 400


# ── Login ─────────────────────────────────────────────────────────────────────

async def test_login_correct_credentials(raw_client: AsyncClient, test_user: User):
    """POST /auth/login → returns JWT."""
    resp = await raw_client.post(
        "/auth/login",
        json={"email": test_user.email, "password": "password123"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(raw_client: AsyncClient, test_user: User):
    """POST /auth/login with wrong password → 401."""
    resp = await raw_client.post(
        "/auth/login",
        json={"email": test_user.email, "password": "wrongpass"},
    )

    assert resp.status_code == 401


async def test_login_unknown_email(raw_client: AsyncClient):
    """POST /auth/login with unknown email → 401."""
    resp = await raw_client.post(
        "/auth/login",
        json={"email": "nobody@test.com", "password": "password123"},
    )

    assert resp.status_code == 401


async def test_login_unverified_email(raw_client: AsyncClient, db_session: AsyncSession):
    """POST /auth/login with unverified email → 403."""
    user = User(
        id=uuid.uuid4(),
        email=f"unverified-{uuid.uuid4().hex[:8]}@test.com",
        password_hash=hash_password("password123"),
        email_verified=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    resp = await raw_client.post(
        "/auth/login",
        json={"email": user.email, "password": "password123"},
    )

    assert resp.status_code == 403


# ── Protected route access ────────────────────────────────────────────────────

async def test_access_protected_without_token():
    """Protected route without Authorization header → 403 (HTTPBearer)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/reviews/")
    # HTTPBearer returns 403 when no credentials present
    assert resp.status_code == 403


async def test_access_protected_with_valid_token(client: AsyncClient, auth_headers: dict):
    """Protected route with valid JWT → 200."""
    resp = await client.get("/reviews/", headers=auth_headers)
    assert resp.status_code == 200


async def test_access_protected_with_invalid_token():
    """Protected route with malformed token → 403."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/reviews/", headers={"Authorization": "Bearer not.a.token"})
    assert resp.status_code in (401, 403)


# ── Telegram webhook ─────────────────────────────────────────────────────────

async def _telegram_update(user_id: str, chat_id: str = "987654321") -> dict:
    return {
        "message": {
            "text": f"/start {user_id}",
            "chat": {"id": int(chat_id), "first_name": "Test"},
        }
    }


async def test_telegram_webhook_valid_uuid(raw_client: AsyncClient, db_session: AsyncSession, test_user: User):
    """Telegram /start with valid user UUID links the account."""
    with patch("app.services.notification.send_telegram", new=AsyncMock()):
        resp = await raw_client.post(
            "/auth/telegram/webhook",
            json=await _telegram_update(str(test_user.id), "111222333"),
        )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    await db_session.refresh(test_user)
    assert test_user.telegram_chat_id == "111222333"


async def test_telegram_webhook_invalid_uuid(raw_client: AsyncClient):
    """Telegram /start with non-UUID payload → returns ok=True, no crash (Bug 3 regression)."""
    resp = await raw_client.post(
        "/auth/telegram/webhook",
        json=await _telegram_update("not-a-uuid", "999888777"),
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


async def test_telegram_webhook_no_payload(raw_client: AsyncClient):
    """/start with no payload (just '/start') → ok=True, no crash."""
    resp = await raw_client.post(
        "/auth/telegram/webhook",
        json={
            "message": {
                "text": "/start",
                "chat": {"id": 123, "first_name": "Bot"},
            }
        },
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


async def test_telegram_webhook_already_linked(raw_client: AsyncClient, db_session: AsyncSession, test_user: User):
    """Telegram webhook does NOT overwrite an already-set telegram_chat_id."""
    test_user.telegram_chat_id = "existing_id"
    await db_session.flush()

    with patch("app.services.notification.send_telegram", new=AsyncMock()):
        resp = await raw_client.post(
            "/auth/telegram/webhook",
            json=await _telegram_update(str(test_user.id), "111000999"),
        )

    assert resp.status_code == 200
    await db_session.refresh(test_user)
    assert test_user.telegram_chat_id == "existing_id"  # unchanged


# ── Google OAuth callback ─────────────────────────────────────────────────────

async def test_oauth_callback_passes_jwt_in_url():
    """GET /auth/callback exchanges code → JWT passed as ?token= query param in redirect URL."""
    # Mock both Google API calls
    token_response = MagicMock()
    token_response.status_code = 200
    token_response.json.return_value = {
        "access_token": "g-access",
        "refresh_token": "g-refresh",
        "expires_in": 3600,
    }
    userinfo_response = MagicMock()
    userinfo_response.status_code = 200
    userinfo_response.json.return_value = {
        "sub": f"google-{uuid.uuid4().hex}",
        "email": f"oauth-{uuid.uuid4().hex[:8]}@test.com",
        "name": "OAuth User",
    }

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=token_response)
    mock_http.get = AsyncMock(return_value=userinfo_response)

    with patch("app.routers.auth.httpx.AsyncClient") as MockClient, \
         patch("app.routers.auth.send_welcome_email", new=AsyncMock()):
        MockClient.return_value.__aenter__.return_value = mock_http

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as ac:
            resp = await ac.get("/auth/callback?code=valid_code")

    # Should redirect
    assert resp.status_code in (302, 307)

    # Token must be present in the redirect URL as a query param
    location = resp.headers.get("location", "")
    assert "token=" in location

    # No HttpOnly cookie should be set
    assert "access_token" not in resp.headers.get("set-cookie", "")


async def test_oauth_callback_missing_code():
    """GET /auth/callback without ?code → 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/auth/callback")
    assert resp.status_code == 422


async def test_oauth_callback_bad_code():
    """GET /auth/callback when Google token exchange fails → 400."""
    bad_response = MagicMock()
    bad_response.status_code = 400
    bad_response.json.return_value = {"error": "invalid_grant"}

    mock_http = AsyncMock()
    mock_http.post = AsyncMock(return_value=bad_response)

    with patch("app.routers.auth.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value = mock_http

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/auth/callback?code=bad")

    assert resp.status_code == 400


# ── Google OAuth redirect ─────────────────────────────────────────────────────

async def test_login_redirects_to_google():
    """GET /auth/login → redirects to Google OAuth."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    ) as ac:
        resp = await ac.get("/auth/login")

    assert resp.status_code in (302, 307)
    location = resp.headers["location"]
    assert "accounts.google.com/o/oauth2/v2/auth" in location
    assert "business.manage" in location
