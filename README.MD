Ось повний professional-grade план з усіма деталями.

🏗️ Повна архітектура системи
text
┌─────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js 14)              │
│  Dashboard → ReviewList → ResponseEditor → Analytics │
└─────────────────┬───────────────────────────────────┘
                  │ REST API / WebSocket
┌─────────────────▼───────────────────────────────────┐
│                 BACKEND (FastAPI)                     │
│  Auth Router │ Reviews Router │ Responses Router      │
│  ─────────────────────────────────────────────────── │
│  GMB Service │ AI Service │ Notification Service      │
│  ─────────────────────────────────────────────────── │
│  Background Tasks (APScheduler)                      │
└──────┬──────────────┬──────────────┬────────────────┘
       │              │              │
  ┌────▼────┐   ┌─────▼─────┐  ┌────▼────┐
  │PostgreSQL│   │ Groq API  │  │ Google  │
  │         │   │ (Llama 3.3)│  │ GMB API │
  └─────────┘   └───────────┘  └─────────┘
📁 Детальна структура файлів
text
ai-review-responder/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app, middleware, routers
│   │   ├── config.py                # Pydantic Settings з .env
│   │   ├── database.py              # SQLAlchemy engine, session
│   │   │
│   │   ├── models/                  # SQLAlchemy ORM моделі
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── review.py
│   │   │   ├── response.py
│   │   │   └── location.py          # GMB локації бізнесу
│   │   │
│   │   ├── schemas/                 # Pydantic схеми (request/response)
│   │   │   ├── user.py
│   │   │   ├── review.py
│   │   │   └── response.py
│   │   │
│   │   ├── routers/
│   │   │   ├── auth.py              # Google OAuth flow
│   │   │   ├── reviews.py           # GET відгуки, sync з GMB
│   │   │   ├── responses.py         # POST генерація, PUT публікація
│   │   │   └── locations.py         # GET локації бізнесу
│   │   │
│   │   ├── services/
│   │   │   ├── llm/
│   │   │   │   ├── base.py          # Abstract LLMProvider
│   │   │   │   ├── groq_provider.py
│   │   │   │   └── factory.py       # get_provider() з .env
│   │   │   ├── gmb_service.py       # Google My Business API client
│   │   │   ├── ai_service.py        # Промпти, генерація відповідей
│   │   │   └── notification.py      # Telegram + Email alerts
│   │   │
│   │   ├── tasks/
│   │   │   └── scheduler.py         # APScheduler: sync відгуків кожні 30хв
│   │   │
│   │   └── core/
│   │       ├── security.py          # JWT токени, OAuth helpers
│   │       └── dependencies.py      # get_db(), get_current_user()
│   │
│   ├── alembic/                     # Міграції БД
│   │   ├── versions/
│   │   └── env.py
│   ├── tests/
│   │   ├── test_reviews.py
│   │   └── test_ai_service.py
│   ├── requirements.txt
│   ├── alembic.ini
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx             # Landing / redirect
│   │   │   ├── auth/
│   │   │   │   └── callback/page.tsx # OAuth callback
│   │   │   └── dashboard/
│   │   │       ├── page.tsx         # Головний дашборд
│   │   │       ├── reviews/page.tsx
│   │   │       └── settings/page.tsx
│   │   │
│   │   ├── components/
│   │   │   ├── ui/                  # shadcn/ui компоненти
│   │   │   ├── ReviewCard.tsx       # Картка відгуку з зірочками
│   │   │   ├── ResponseEditor.tsx   # AI відповідь + редактор
│   │   │   ├── ToneSelector.tsx     # formal/warm/casual
│   │   │   └── StatsWidget.tsx      # Кількість відповідей, середній рейтинг
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts               # axios клієнт до backend
│   │   │   └── auth.ts              # NextAuth або custom auth
│   │   │
│   │   └── types/
│   │       └── index.ts             # TypeScript типи
│   │
│   ├── package.json
│   ├── tailwind.config.ts
│   └── Dockerfile
│
├── nginx/
│   └── nginx.conf                   # Reverse proxy, SSL
├── docker-compose.yml               # Production
├── docker-compose.dev.yml           # Local development
├── .env.example
├── .gitignore
└── README.md
🗄️ Database Schema (повна)
sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    business_name VARCHAR(255),
    google_id VARCHAR(255) UNIQUE,
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    tone_preference VARCHAR(20) DEFAULT 'warm',  -- formal/warm/casual
    language VARCHAR(10) DEFAULT 'auto',          -- auto/fr/en
    plan VARCHAR(20) DEFAULT 'free',              -- free/starter/pro
    created_at TIMESTAMP DEFAULT NOW()
);

-- GMB Locations (бізнес може мати кілька локацій)
CREATE TABLE locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    gmb_location_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    address TEXT,
    is_active BOOLEAN DEFAULT true
);

-- Reviews
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    location_id UUID REFERENCES locations(id) ON DELETE CASCADE,
    gmb_review_id VARCHAR(255) UNIQUE NOT NULL,
    author_name VARCHAR(255),
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    language VARCHAR(10),                         -- auto-detected
    review_date TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',         -- pending/responded/ignored
    synced_at TIMESTAMP DEFAULT NOW()
);

-- Responses
CREATE TABLE responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID REFERENCES reviews(id) ON DELETE CASCADE,
    ai_draft TEXT NOT NULL,
    final_text TEXT,
    tone_used VARCHAR(20),
    model_used VARCHAR(50),                       -- llama-3.3-70b-versatile
    was_edited BOOLEAN DEFAULT false,
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
🔧 Ключові файли — стартовий код
backend/app/config.py
python
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
        env_file = ".env"

settings = Settings()
backend/app/services/llm/base.py
python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ReviewContext:
    review_text: str
    business_name: str
    rating: int
    tone: str = "warm"        # formal / warm / casual
    language: str = "auto"    # auto-detect з відгуку

class LLMProvider(ABC):
    @abstractmethod
    async def generate_response(self, context: ReviewContext) -> str:
        pass
backend/app/services/llm/groq_provider.py
python
from groq import AsyncGroq
from .base import LLMProvider, ReviewContext

TONE_INSTRUCTIONS = {
    "formal": "professional and formal",
    "warm": "friendly and warm",
    "casual": "casual and relaxed"
}

class GroqProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.client = AsyncGroq(api_key=api_key)

    async def generate_response(self, context: ReviewContext) -> str:
        tone_desc = TONE_INSTRUCTIONS[context.tone]
        
        system_prompt = f"""You are a {tone_desc} customer service manager 
        for "{context.business_name}". 
        CRITICAL RULES:
        - Respond in the EXACT same language as the review
        - Keep response under 150 words
        - Be specific to what the customer mentioned
        - Never use generic phrases like "Thank you for your feedback"
        - For 1-2 star reviews: empathize and offer solution
        - For 4-5 star reviews: be grateful and reinforce positives"""

        response = await self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Review ({context.rating}/5 stars):\n{context.review_text}"}
            ],
            max_tokens=250,
            temperature=0.75
        )
        return response.choices[0].message.content
backend/app/services/llm/factory.py
python
from app.config import settings
from .base import LLMProvider
from .groq_provider import GroqProvider

def get_llm_provider() -> LLMProvider:
    providers = {
        "groq": lambda: GroqProvider(settings.GROQ_API_KEY),
        # "mistral": lambda: MistralProvider(settings.MISTRAL_API_KEY),
        # "gemini": lambda: GeminiProvider(settings.GEMINI_API_KEY),
    }
    return providers[settings.LLM_PROVIDER]()
docker-compose.dev.yml
text
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: reviewuser
      POSTGRES_PASSWORD: reviewpass
      POSTGRES_DB: reviewdb
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    command: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - postgres

  frontend:
    build: ./frontend
    command: npm run dev
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "3000:3000"
    env_file: .env

volumes:
  postgres_data:
📋 Промпти для Claude — покроково
Відкриваєш VS Code, запускаєш Claude Code і даєш промпти в такому порядку:

Промпт 1 — Ініціалізація:

"Ініціалізуй FastAPI проєкт за такою структурою: [вставити структуру]. Встанови залежності: fastapi, uvicorn, sqlalchemy, alembic, asyncpg, pydantic-settings, groq, python-jose, httpx, apscheduler. Створи базовий main.py з CORS middleware, підключенням до PostgreSQL. Створи docker-compose.dev.yml з postgres і backend."

Промпт 2 — Database + Alembic:

"Створи SQLAlchemy моделі для users, locations, reviews, responses за цією SQL схемою: [вставити schema]. Налаштуй Alembic, зроби першу міграцію initial_schema."

Промпт 3 — Google OAuth:

"Реалізуй Google OAuth 2.0 flow в routers/auth.py. GET /auth/login → redirect на Google. GET /auth/callback → отримати tokens, зберегти в users таблицю, повернути JWT. Scopes: openid, email, profile, https://www.googleapis.com/auth/business.manage."

Промпт 4 — GMB Service:

"Створи gmb_service.py. Методи: get_locations(access_token) → список локацій бізнесу з Google Business Profile API v1. sync_reviews(location_id, access_token) → отримати всі відгуки і зберегти в БД уникаючи дублікатів по gmb_review_id. publish_response(review_name, response_text, access_token) → опублікувати відповідь."

Промпт 5 — AI Service + Groq:

"Додай LLM абстракцію з файлів [вставити groq_provider.py вище]. Створи ai_service.py з методом generate_and_save(review_id, db) який бере відгук з БД, генерує відповідь через GroqProvider, зберігає в таблицю responses зі статусом draft."

Промпт 6 — Background Scheduler:

"Налаштуй APScheduler в tasks/scheduler.py. Кожні 30 хвилин: для кожного активного user → sync_reviews для кожної location → якщо нові відгуки → надіслати Telegram alert через Bot API."

Промпт 7 — Frontend:

"Створи Next.js 14 дашборд з Tailwind і shadcn/ui. Сторінки: /dashboard — статистика (всього відгуків, % відповідей, середній рейтинг), список останніх відгуків. ReviewCard компонент: зірочки рейтингу, текст відгуку, кнопка 'Generate AI Response'. ResponseEditor: textarea з AI текстом, ToneSelector (formal/warm/casual), кнопки Regenerate / Publish."

Промпт 8 — Production Deploy:

"Зроби production docker-compose.yml з nginx reverse proxy, SSL через Let's Encrypt (certbot). Backend і frontend в окремих контейнерах. Nginx проксує /api → backend:8000, / → frontend:3000."

⏱️ Детальний таймлайн
День	Завдання	Результат
День 1	Промпти 1-2: setup + DB	Docker запущений, БД з міграціями
День 2	Промпт 3: Google OAuth	Логін через Google працює
День 3	Промпти 4-5: GMB + Groq	Відгуки синхронізуються, AI генерує
День 4	Промпт 6: Scheduler	Автоматичний sync + Telegram алерти
День 5	Промпт 7: Frontend	Дашборд з UI
День 6	Промпт 8: Deploy	Live на сервері