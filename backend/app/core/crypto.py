"""
Symmetric token encryption using Fernet (AES-128-CBC + HMAC-SHA256).

Key generation (run once, store in .env as TOKEN_ENCRYPTION_KEY):
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

If TOKEN_ENCRYPTION_KEY is empty, encrypt/decrypt are no-ops — plain text is
stored as-is.  This lets you deploy encryption incrementally: set the key, and
on the next OAuth login the tokens will be stored encrypted; the fallback in
decrypt_token handles any remaining plain-text values already in the DB.
"""
import logging

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_fernet: Fernet | None = None
_fernet_loaded = False


def _get_fernet() -> Fernet | None:
    global _fernet, _fernet_loaded
    if _fernet_loaded:
        return _fernet
    _fernet_loaded = True

    from app.config import settings
    key = settings.TOKEN_ENCRYPTION_KEY
    if not key:
        _fernet = None
        return None

    try:
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:
        logger.error("Invalid TOKEN_ENCRYPTION_KEY — encryption disabled: %s", exc)
        _fernet = None
    return _fernet


def encrypt_token(plain: str) -> str:
    """Encrypt a plain-text token. Returns plain text if no key is configured."""
    if not plain:
        return plain
    f = _get_fernet()
    if f is None:
        return plain
    return f.encrypt(plain.encode()).decode()


def decrypt_token(value: str) -> str:
    """Decrypt a Fernet-encrypted token.

    Falls back to returning the value as-is for:
    - legacy plain-text tokens already in the DB
    - environments where TOKEN_ENCRYPTION_KEY is not set
    """
    if not value:
        return value
    f = _get_fernet()
    if f is None:
        return value
    try:
        return f.decrypt(value.encode()).decode()
    except (InvalidToken, Exception):
        # Token is likely plain-text (stored before encryption was enabled)
        return value
