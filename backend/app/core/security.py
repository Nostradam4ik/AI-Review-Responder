from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def create_email_token(email: str, purpose: str, expires_minutes: int = 60) -> str:
    """Short-lived JWT for email verification / password reset."""
    return create_access_token(
        {"sub": email, "purpose": purpose},
        expires_delta=timedelta(minutes=expires_minutes),
    )


def decode_email_token(token: str, purpose: str) -> str:
    """Decode and validate email token, return email or raise ValueError."""
    try:
        data = decode_access_token(token)
    except Exception:
        raise ValueError("Invalid or expired token")
    if data.get("purpose") != purpose:
        raise ValueError("Token purpose mismatch")
    return data["sub"]
