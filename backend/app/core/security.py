from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from app.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": now.timestamp()})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    import secrets
    jti = secrets.token_urlsafe(32)
    return create_access_token(
        {"sub": user_id, "type": "refresh", "jti": jti},
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def _get_email_secret() -> str:
    from app.config import settings
    return settings.EMAIL_SECRET_KEY or settings.SECRET_KEY


def create_email_token(email: str, purpose: str, expires_minutes: int = 60) -> str:
    """Short-lived JWT for email verification / password reset."""
    now = datetime.now(timezone.utc)
    to_encode = {
        "sub": email,
        "purpose": purpose,
        "exp": now + timedelta(minutes=expires_minutes),
        "iat": now.timestamp(),
    }
    return jwt.encode(to_encode, _get_email_secret(), algorithm=ALGORITHM)


def decode_email_token(token: str, purpose: str) -> str:
    """Decode and validate email token, return email or raise ValueError."""
    try:
        data = jwt.decode(token, _get_email_secret(), algorithms=[ALGORITHM])
    except Exception:
        raise ValueError("Invalid or expired token")
    if data.get("purpose") != purpose:
        raise ValueError("Token purpose mismatch")
    return data["sub"]
