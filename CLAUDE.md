# AI Review Responder — Project Context

## What it is
SaaS for restaurants and hotels to automatically respond to Google Business reviews using AI.
Target market: France-based local businesses (restaurants, hotels, cafés).

## Tech Stack
- Frontend: Next.js 14, TypeScript, Tailwind CSS, next-intl (6 languages)
- Backend: FastAPI, Python, PostgreSQL, SQLAlchemy async, Alembic migrations
- Infrastructure: Docker Compose, Hetzner VPS (production)
- Payments: Stripe (checkout + webhooks)
- Notifications: Telegram Bot (@ReviewAIresponderbot)
- Email: Resend
- AI: OpenAI API (GPT-4o)
- Auth: Google OAuth + email/password

## Business Model
14-day free trial (all features) → paid subscription:
- Starter €19/mo: 1 location, 100 AI responses/mo, no CSV/auto-publish/templates
- Pro €39/mo: 3 locations, unlimited, all features
- Agency €79/mo: 10 locations, unlimited, all features + dedicated support

## Database Migrations
Current: 001 → 007
Always create new migration file in backend/alembic/versions/ and run:
docker exec ai-review-responder-backend-1 alembic upgrade head

## Key Files
- backend/app/routers/reviews.py — reviews sync, AI generate, CSV export
- backend/app/routers/auth.py — Google OAuth, email auth, Telegram webhook
- backend/app/core/dependencies.py — plan feature gates (require_plan_feature)
- backend/app/tasks/scheduler.py — background review sync every 30 minutes
- frontend/app/dashboard/reviews/page.tsx — reviews UI
- frontend/app/dashboard/settings/page.tsx — settings UI
- frontend/app/onboarding/page.tsx — 3-step onboarding wizard

## Important Decisions
- Telegram: per-user chat_id stored in users.telegram_chat_id
  Connection flow: t.me/ReviewAIresponderbot?start=<user_id>
- Feature gates: trial_expired → 402, feature_not_available → 402
  Frontend api.ts interceptor catches 402 → redirect to /dashboard/billing
- i18n: next-intl, 6 languages in frontend/messages/
- Notifications: Telegram first, email fallback via Resend if no telegram_chat_id

## Production TODOs
After deploying to Hetzner:
1. Register Stripe webhook: stripe listen --forward-to https://yourdomain.com/billing/webhook
2. Register Telegram webhook: POST https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://yourdomain.com/auth/telegram/webhook
3. Set all env vars in .env.production
