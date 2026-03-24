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
    SECRET_KEY: str
    LLM_PROVIDER: str = "groq"
    FRONTEND_URL: str = "http://localhost:3000"
    APP_URL: str = "http://localhost:3000"

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_PRO: str = ""
    STRIPE_PRICE_AGENCY: str = ""

    # Resend (email)
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "noreply@yourapp.com"
    # Set to true in dev to skip email verification (useful when Resend domain isn't verified)
    AUTO_VERIFY_EMAIL: bool = False

    class Config:
        env_file = (".env", "../.env")


settings = Settings()
