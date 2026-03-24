from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import (
    create_access_token,
    create_email_token,
    decode_email_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.subscription import Subscription
from app.models.user import User
from app.services.email_service import send_reset_email, send_verification_email

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


# ── Email / password auth ────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    business_name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Create account with email/password, send verification email."""
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(409, "An account with this email already exists")

    auto_verify = settings.AUTO_VERIFY_EMAIL

    user = User(
        email=body.email,
        business_name=body.business_name or None,
        password_hash=hash_password(body.password),
        email_verified=auto_verify,
        onboarding_done=bool(body.business_name),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    db.add(Subscription(
        user_id=user.id,
        plan_id="starter",
        status="trialing",
        trial_end=datetime.now(timezone.utc) + timedelta(days=14),
    ))
    await db.flush()

    if auto_verify:
        return {"message": "Account created. You can now sign in.", "verified": True}

    token = create_email_token(body.email, "verify")
    await send_verification_email(body.email, token)

    return {"message": "Account created. Check your email to verify your address.", "verified": False}


@router.post("/login")
async def login_email(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email/password, return JWT."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")

    if not user.email_verified:
        raise HTTPException(403, "Please verify your email before logging in")

    jwt_token = create_access_token({"sub": str(user.id)})
    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "onboarding_done": user.onboarding_done,
    }


@router.get("/verify-email")
async def verify_email(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Verify email address via token from the verification email."""
    try:
        email = decode_email_token(token, "verify")
    except ValueError as e:
        raise HTTPException(400, str(e))

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    user.email_verified = True
    await db.commit()

    return RedirectResponse(f"{settings.FRONTEND_URL}/login?verified=1")


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Send password-reset email (always returns 200 to avoid user enumeration)."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user and user.password_hash:
        token = create_email_token(body.email, "reset")
        await send_reset_email(body.email, token)
    return {"message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Apply new password from reset token."""
    try:
        email = decode_email_token(body.token, "reset")
    except ValueError as e:
        raise HTTPException(400, str(e))

    if len(body.new_password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"message": "Password updated successfully"}


# ── Telegram webhook ─────────────────────────────────────────────────────────


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle incoming Telegram updates.

    When a user opens the deep link t.me/<bot>?start=<user_id>,
    Telegram sends a message /start <user_id> to this webhook.
    We use the payload to link the Telegram chat_id to the user account.
    """
    try:
        data = await request.json()
    except Exception:
        return {"ok": True}

    message = data.get("message") or data.get("edited_message") or {}
    text: str = message.get("text", "")
    chat = message.get("chat", {})
    chat_id = str(chat.get("id", ""))
    first_name = chat.get("first_name", "")

    if not text.startswith("/start") or not chat_id:
        return {"ok": True}

    parts = text.split(maxsplit=1)
    payload = parts[1].strip() if len(parts) > 1 else ""

    if payload:
        # payload is the user_id UUID
        result = await db.execute(select(User).where(User.id == payload))
        user = result.scalar_one_or_none()
        if user and not user.telegram_chat_id:
            user.telegram_chat_id = chat_id
            await db.commit()

            # Send confirmation to user
            from app.services.notification import send_telegram
            name = user.business_name or user.email
            await send_telegram(
                f"✅ <b>Telegram connected!</b>\n\n"
                f"Account: {name}\n"
                f"You'll receive review notifications here.",
                chat_id=chat_id,
            )

    return {"ok": True}
