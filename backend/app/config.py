from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    GROQ_API_KEY: str
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    SECRET_KEY: str
    LLM_PROVIDER: str = "groq"
    FRONTEND_URL: str = "http://localhost:3000"

    class Config:
        env_file = (".env", "../.env")


settings = Settings()
