import hmac
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.crypto import encrypt_token
from app.core.limiter import limiter
from app.core.security import (
    create_access_token,
    create_email_token,
    create_refresh_token,
    decode_access_token,
    decode_email_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.subscription import Subscription
from app.models.user import User
from app.services.email_service import send_reset_email, send_verification_email, send_welcome_email

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

    user.access_token = encrypt_token(access_token)
    if refresh_token:
        user.refresh_token = encrypt_token(refresh_token)
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
        user.plan = "starter"
        await db.flush()
        await send_welcome_email(user.email, user.business_name or user.email)

    jwt_token = create_access_token({"sub": str(user.id)})
    refresh = create_refresh_token(str(user.id))
    user.refresh_token_jti = decode_access_token(refresh)["jti"]
    response = RedirectResponse(f"{settings.FRONTEND_URL}/auth/callback#token={jwt_token}")
    response.set_cookie(
        "refresh_token", refresh,
        httponly=True, secure=True, samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return response


@router.get("/mock-login")
async def mock_login(db: AsyncSession = Depends(get_db)):
    """Return a JWT for test@test.com — development only."""
    from app.config import settings
    if settings.ENVIRONMENT not in ("development", "test"):
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
    password: str = Field(..., min_length=8, max_length=128)
    business_name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


@router.post("/register", status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Create account with email/password, send verification email."""
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if len(body.password) > 128:
        raise HTTPException(400, "Password must not exceed 128 characters")

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
    user.plan = "starter"
    await db.flush()
    await send_welcome_email(user.email, body.business_name or user.email)

    if auto_verify:
        return {"message": "Account created. You can now sign in.", "verified": True}

    token = create_email_token(body.email, "verify")
    await send_verification_email(body.email, token)

    return {"message": "Account created. Check your email to verify your address.", "verified": False}


@router.post("/login")
@limiter.limit("5/minute")
async def login_email(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email/password, return JWT."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")

    if not user.email_verified:
        raise HTTPException(403, "Please verify your email before logging in")

    jwt_token = create_access_token({"sub": str(user.id)})
    refresh = create_refresh_token(str(user.id))
    user.refresh_token_jti = decode_access_token(refresh)["jti"]
    from fastapi.responses import JSONResponse
    response = JSONResponse({
        "access_token": jwt_token,
        "token_type": "bearer",
        "onboarding_done": user.onboarding_done,
    })
    response.set_cookie(
        "refresh_token", refresh,
        httponly=True, secure=True, samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return response


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
@limiter.limit("5/minute")
async def forgot_password(request: Request, body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
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
        raw_payload = decode_access_token(body.token)
        token_iat = raw_payload.get("iat", 0)
    except ValueError as e:
        raise HTTPException(400, str(e))

    if len(body.new_password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if len(body.new_password) > 128:
        raise HTTPException(400, "Password must not exceed 128 characters")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    if user.password_changed_at:
        changed_ts = user.password_changed_at.timestamp()
        if token_iat <= changed_ts:
            raise HTTPException(400, "Reset link has already been used")

    user.password_hash = hash_password(body.new_password)
    user.password_changed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Password updated successfully"}


# ── Token refresh ────────────────────────────────────────────────────────────


@router.post("/refresh")
async def refresh_token(request: Request, db: AsyncSession = Depends(get_db)):
    """Exchange httpOnly refresh token cookie for a new access token."""
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    from jose import JWTError
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(401, "Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(401, "Not a refresh token")

    user_id = payload.get("sub")
    try:
        user = await db.get(User, uuid.UUID(user_id))
    except (ValueError, TypeError):
        raise HTTPException(401, "Invalid token subject")

    if not user or not user.is_active:
        raise HTTPException(401, "User not found")

    if payload.get("jti") != user.refresh_token_jti:
        raise HTTPException(401, "Token has been revoked")

    new_access_token = create_access_token({"sub": user_id})
    new_refresh = create_refresh_token(user_id)
    user.refresh_token_jti = decode_access_token(new_refresh)["jti"]

    from fastapi.responses import JSONResponse
    response = JSONResponse({"access_token": new_access_token, "token_type": "bearer"})
    response.set_cookie(
        "refresh_token", new_refresh,
        httponly=True, secure=True, samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return response


@router.post("/logout")
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    """Clear the httpOnly refresh token cookie and revoke the refresh token JTI."""
    from fastapi.responses import JSONResponse
    from jose import JWTError

    token = request.cookies.get("refresh_token")
    if token:
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
            if user_id:
                user = await db.get(User, uuid.UUID(user_id))
                if user:
                    user.refresh_token_jti = None
        except (JWTError, ValueError):
            pass  # best-effort: always clear the cookie even if token is invalid

    response = JSONResponse({"logged_out": True})
    response.delete_cookie("refresh_token", httponly=True, secure=True, samesite="lax")
    return response


# ── Telegram webhook ─────────────────────────────────────────────────────────


@router.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Handle incoming Telegram updates.

    When a user opens the deep link t.me/<bot>?start=<user_id>,
    Telegram sends a message /start <user_id> to this webhook.
    We use the payload to link the Telegram chat_id to the user account.
    """
    expected_secret = settings.TELEGRAM_WEBHOOK_SECRET
    if settings.TELEGRAM_BOT_TOKEN:
        if not x_telegram_bot_api_secret_token or not expected_secret or not hmac.compare_digest(
            x_telegram_bot_api_secret_token, expected_secret
        ):
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

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
        try:
            uid = uuid.UUID(payload)
        except ValueError:
            return {"ok": True}
        result = await db.execute(select(User).where(User.id == uid))
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
