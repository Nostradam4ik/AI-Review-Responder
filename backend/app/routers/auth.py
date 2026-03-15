from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import create_access_token
from app.database import get_db
from app.models.subscription import Subscription
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/business.manage",
]


@router.get("/login")
async def login():
    """Redirect user to Google OAuth consent screen."""
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url)


@router.get("/callback")
async def callback(
    code: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback, exchange code for tokens, upsert user."""
    async with httpx.AsyncClient() as client:
        # Exchange code for tokens
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code for tokens")

        token_data = token_resp.json()
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)
        token_expires_at = datetime.now(timezone.utc).timestamp() + expires_in

        # Fetch user info
        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch user info")

        userinfo = userinfo_resp.json()
        google_id = userinfo["sub"]
        email = userinfo["email"]
        name = userinfo.get("name")

    # Upsert user
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if user is None:
        # Check if email already exists (user signed up differently)
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    is_new_user = user is None
    if user is None:
        user = User(
            email=email,
            business_name=name,
            google_id=google_id,
        )
        db.add(user)

    user.access_token = access_token
    user.refresh_token = refresh_token or user.refresh_token
    user.token_expires_at = datetime.fromtimestamp(token_expires_at, tz=timezone.utc)
    user.google_id = google_id

    await db.flush()
    await db.refresh(user)

    # Create 14-day trial subscription for new users
    if is_new_user:
        db.add(Subscription(
            user_id=user.id,
            plan_id="starter",
            status="trialing",
            trial_end=datetime.now(timezone.utc) + timedelta(days=14),
        ))
        await db.flush()

    # Issue our own JWT
    jwt_token = create_access_token({"sub": str(user.id)})

    # Redirect to frontend with token
    return RedirectResponse(
        f"{settings.FRONTEND_URL}/auth/callback?token={jwt_token}"
    )


@router.get("/me")
async def me(db: AsyncSession = Depends(get_db)):
    """Placeholder — real version uses get_current_user dependency."""
    return {"message": "Use Authorization: Bearer <token> header"}


@router.get("/mock-login")
async def mock_login(db: AsyncSession = Depends(get_db)):
    """Return a JWT for test@test.com — development only."""
    from app.config import settings
    if "localhost" not in settings.DATABASE_URL and "postgres" not in settings.DATABASE_URL:
        raise HTTPException(status_code=403, detail="Only available in development")

    result = await db.execute(select(User).where(User.email == "test@test.com"))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Mock user not found — call POST /reviews/seed-mock first")

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}
