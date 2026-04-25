from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    GROQ_API_KEY: str
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_BOT_USERNAME: str = "ReviewAIresponderbot"
    TELEGRAM_WEBHOOK_SECRET: str = ""
    SECRET_KEY: str
    EMAIL_SECRET_KEY: str = ""
    # If empty, falls back to SECRET_KEY (backward compatible)
    # Generate: python -c "import secrets; print(secrets.token_hex(32))"
    LLM_PROVIDER: Literal["groq"] = "groq"
    FRONTEND_URL: str = "http://localhost:3000"
    APP_URL: str = "http://localhost:3000"

    # CORS — in production set to your real domain(s):
    # ALLOWED_ORIGINS=["https://yourdomain.com","https://www.yourdomain.com"]
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_min_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    ENVIRONMENT: str = "production"

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if not self.ENVIRONMENT:
            raise ValueError(
                "ENVIRONMENT must be set explicitly in .env — use 'development' or 'production'"
            )
        if self.ENVIRONMENT == "production" and not self.TOKEN_ENCRYPTION_KEY:
            raise ValueError(
                "TOKEN_ENCRYPTION_KEY is required in production. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\""
            )
        if self.TOKEN_ENCRYPTION_KEY and len(self.TOKEN_ENCRYPTION_KEY) < 32:
            raise ValueError("TOKEN_ENCRYPTION_KEY must be at least 32 characters if set")
        if self.ENVIRONMENT == "production" and "*" in self.ALLOWED_ORIGINS:
            raise ValueError("Wildcard CORS origin '*' is not allowed in production")
        if self.TELEGRAM_BOT_TOKEN and not self.TELEGRAM_WEBHOOK_SECRET:
            raise ValueError(
                "TELEGRAM_WEBHOOK_SECRET is required when TELEGRAM_BOT_TOKEN is set. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return self

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ID_STARTER: str = ""
    STRIPE_PRICE_ID_PRO: str = ""
    STRIPE_PRICE_ID_AGENCY: str = ""

    # Token encryption — generate with:
    # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    TOKEN_ENCRYPTION_KEY: str = ""

    REDIS_URL: str = "redis://localhost:6379/0"

    # Sentry error tracking (optional — leave empty to disable)
    SENTRY_DSN: str | None = None

    # Resend (email)
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "noreply@yourapp.com"
    # Set to true in dev to skip email verification (useful when Resend domain isn't verified)
    AUTO_VERIFY_EMAIL: bool = False

    class Config:
        env_file = (".env", "../.env")
        extra = "ignore"


settings = Settings()
