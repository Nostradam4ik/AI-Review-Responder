# AI Review Responder

![CI](https://github.com/Nostradam4ik/AI-Review-Responder/actions/workflows/ci.yml/badge.svg)

SaaS platform for restaurants and hotels to automatically respond to Google Business reviews using AI.

## Stack

- **Backend**: FastAPI, Python 3.12, PostgreSQL, SQLAlchemy async, Alembic
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, next-intl (6 languages)
- **AI**: Groq API
- **Payments**: Stripe (checkout + webhooks)
- **Auth**: Google OAuth + email/password
- **Notifications**: Telegram Bot, Resend email

## Plans

| Plan | Price | Locations | AI Responses/mo |
|------|-------|-----------|-----------------|
| Starter | €19/mo | 1 | 100 |
| Pro | €39/mo | 3 | Unlimited |
| Agency | €79/mo | 10 | Unlimited |

14-day free trial included on all plans.

## Local development

```bash
cp .env.example .env
# fill in .env values

docker compose -f docker-compose.dev.yml up --build
```

Backend: `http://localhost:8000` · Frontend: `http://localhost:3000`

## Running tests

```bash
docker exec ai-review-responder-backend-1 \
  python -m pytest tests/ -v --tb=short
```

## Environment variables

See [.env.example](.env.example) for all required variables.

Required in production:
- `DATABASE_URL` — PostgreSQL connection string
- `SECRET_KEY` — JWT signing secret
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI`
- `GROQ_API_KEY`
- `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET`
