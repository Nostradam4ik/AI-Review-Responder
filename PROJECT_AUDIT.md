# Project Audit — AI Review Responder

Audit date: 2026-04-16  
Auditor: Claude (full static read of every source file)

---

## 1. Project Overview

**Product:** SaaS for French restaurants, hotels, and cafés to automatically respond to Google Business reviews using AI.

**Tech stack:**
| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, next-intl (6 locales) |
| Backend | FastAPI (Python 3.12), SQLAlchemy async, Alembic |
| Database | PostgreSQL 16 |
| AI / LLM | Groq API (llama-3.3-70b-versatile) |
| Payments | Stripe (Checkout + webhooks) |
| Auth | Google OAuth 2.0 + email/password (JWT in localStorage) |
| Notifications | Telegram Bot + Resend email fallback |
| Infra | Docker Compose, Hetzner VPS (prod), nginx + Let's Encrypt |

**Business model:** 14-day free trial (all features unlocked) → paid subscription:
- **Starter** €19/mo — 1 location, 100 AI responses/month, no analytics/CSV/auto-publish
- **Pro** €39/mo — 3 locations, 500 responses/month, all features
- **Agency** €79/mo — 10 locations, 2000 responses/month, all features + priority support

**Repository structure:**
```
backend/          FastAPI app (app/), Alembic migrations, tests/
frontend/         Next.js app (app/, components/, lib/, hooks/)
docker-compose.dev.yml
docker-compose.prod.yml
.env.example
```

---

## 2. Database Schema

13 migrations (001–013), current head: `013_abuse_protection`.

### Tables

**users**
- `id` UUID PK, `email` unique, `business_name`, `google_id` unique nullable
- `access_token` / `refresh_token` / `token_expires_at` — Google OAuth tokens (optionally Fernet-encrypted)
- `tone_preference` default "warm", `language` default "auto", `plan` default "free" (denormalized, kept in sync manually)
- `password_hash`, `email_verified`, `onboarding_done`
- `telegram_chat_id`, `auto_publish`, `response_instructions`
- `is_admin`, `is_active`, `created_at`
- **Missing indexes:** no index on `created_at`, no index on `is_active`

**locations**
- `id` UUID PK, `user_id` FK→users CASCADE, `gmb_location_id` unique, `name`, `address`, `is_active`

**reviews**
- `id` UUID PK, `location_id` FK→locations CASCADE
- `gmb_review_id` unique, `author_name`, `rating` (1–5, CHECK constraint), `comment`, `language`
- `review_date`, `status` (pending/responded/ignored), `priority_score` default 0, `synced_at`
- **Missing indexes:** no index on `(location_id, review_date)`, `status`, `priority_score`

**responses**
- `id` UUID PK, `review_id` FK→reviews CASCADE
- `ai_draft`, `final_text`, `tone_used`, `model_used`, `was_edited`, `published_at`, `created_at`

**plans**
- `id` STRING PK (starter/pro/agency), `name`, `stripe_price_id` (empty in seeds!), `price_eur`
- `max_locations`, `max_responses_per_month`, `features` JSONB

**subscriptions**
- `id` UUID PK, `user_id` FK UNIQUE (one sub per user), `plan_id` FK→plans
- `stripe_subscription_id`, `stripe_customer_id`
- `status` (trialing/active/canceled), `current_period_start/end`, `trial_end`, `created_at`
- `responses_limit_override` nullable (admin override: -1=unlimited, N=custom cap)

**usage_logs**
- `id`, `user_id` FK, `action_type` (ai_generate/ai_publish), `billing_period` (YYYY-MM), `created_at`
- Index: `(user_id, billing_period)`

**analytics_cache**
- `id` UUID PK, `user_id` FK, `location_id` nullable, `period` (week/month)
- `cache_date` DATE, `result` JSONB, `expires_at`, `was_cache_hit` BOOL, `created_at`
- Index: `(user_id, location_id, period, cache_date)`

**review_collection_links**
- `id` UUID PK, `location_id` FK→locations CASCADE, `slug` unique, `google_maps_url`, `is_active`, `created_at`

**internal_feedback**
- `id` UUID PK, `link_id` FK→review_collection_links CASCADE, `rating`, `comment`, `created_at`

### Schema notes
- No `google_id` field on `auth/me` — confirmed: `GET /auth/me` is a placeholder that returns a string. The real profile comes from `GET /users/me`.
- Migration 013 corrects Pro/Agency `max_responses_per_month` to 500/2000 from the earlier 0 (unlimited). The test `conftest.py` still seeds Pro with `max_responses_per_month=0`, creating a test/prod divergence.
- Migration 012 guards with `if "analytics_cache" not in existing` — safe for re-runs.

---

## 3. API Endpoints Map

Base URL: `http://localhost:8000` (dev)

### Auth (`/auth`)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/auth/login` | — | Redirect to Google OAuth |
| GET | `/auth/callback` | — | OAuth code exchange, sets HttpOnly cookie, redirects |
| GET | `/auth/me` | — | **Placeholder only** — returns a static string, not user data |
| GET | `/auth/mock-login` | — | Dev only: returns JWT for test@test.com |
| POST | `/auth/register` | — | Email registration + 14-day trial creation |
| POST | `/auth/login` | — | Email/password login |
| GET | `/auth/verify-email` | — | Email verification by token |
| POST | `/auth/forgot-password` | — | Send reset email |
| POST | `/auth/reset-password` | — | Apply new password |
| POST | `/auth/telegram/webhook` | — | Telegram bot webhook (links chat_id) |

### Users (`/users`)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/users/me` | JWT | Full user profile |
| PATCH | `/users/me` | JWT | Update profile (tone, language, auto_publish, etc.) |
| POST | `/users/me/change-password` | JWT | Change password (email-auth accounts only) |
| GET | `/users/me/telegram-status` | JWT | Whether Telegram is connected |
| DELETE | `/users/me/telegram` | JWT | Disconnect Telegram |

### Locations (`/locations`)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/locations/` | JWT | List user's saved locations |
| POST | `/locations/sync` | JWT | Fetch & sync from GMB API |

### Reviews (`/reviews`)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/reviews/` | JWT | List with filters (status, date, location, search, pagination) |
| POST | `/reviews/sync` | JWT | Trigger GMB review sync |
| PATCH | `/reviews/{id}/status` | JWT | Update status (pending/responded/ignored) |
| GET | `/reviews/export/csv` | JWT + Pro | CSV export |
| POST | `/reviews/seed-demo` | JWT | Seed demo reviews |
| POST | `/reviews/test-telegram` | JWT | Test Telegram notification |
| POST | `/reviews/seed-mock` | — | Dev only: seed mock reviews |

### Responses (`/responses`)
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/responses/generate` | JWT | Generate AI draft + optional auto-publish |
| PUT | `/responses/{id}` | JWT | Edit response text |
| POST | `/responses/{id}/publish` | JWT | Publish to GMB |
| GET | `/responses/review/{review_id}` | JWT | Get existing response for a review |

### Analytics (`/analytics`)
| Method | Path | Auth | Plan |
|---|---|---|---|
| GET | `/analytics` | JWT | Pro+ |
| GET | `/analytics/report/preview` | JWT | Pro+ |
| GET | `/analytics/report/download` | JWT | Pro+ |

### Billing (`/billing`)
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/billing/checkout` | JWT | Create Stripe Checkout session |
| POST | `/billing/webhook` | — | Stripe webhook (signature-verified) |
| GET | `/billing/status` | JWT | Subscription + usage status |
| POST | `/billing/portal` | JWT | Stripe Customer Portal link |

### Collection Links (`/collection`, `/c`)
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/collection/links` | JWT | Create QR/NFC review link |
| GET | `/collection/links` | JWT | List user's links |
| GET | `/collection/links/{id}/stats` | JWT | Internal feedback stats |
| GET | `/c/{slug}` | — | Public star-rating HTML page |
| POST | `/c/{slug}/feedback` | — | Submit feedback (1-3 → private, 4-5 → Google Maps redirect) |

### Admin (`/admin`)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/admin/stats` | JWT + admin | Platform KPIs |
| GET | `/admin/users` | JWT + admin | Paginated user list with search |
| POST | `/admin/users/{id}/reset-trial` | JWT + admin | Reset 14-day trial |
| POST | `/admin/users/{id}/change-plan` | JWT + admin | Change plan |
| PUT | `/admin/users/{id}` | JWT + admin | Full subscription edit |
| GET | `/admin/cost-monitor` | JWT + admin | LLM cost visibility |
| DELETE | `/admin/users/{id}` | JWT + admin | Soft-delete user |

### System
| Method | Path | Description |
|---|---|---|
| GET | `/health` | DB connectivity check |

---

## 4. Feature Completeness Matrix

| Feature | Backend | Frontend | Tests | Notes |
|---|---|---|---|---|
| Google OAuth login | ✅ | ❌ BROKEN | Partial | Frontend reads token from URL; backend puts it in cookie |
| Email/password auth | ✅ | ✅ | ✅ | |
| Email verification | ✅ | ✅ | ✅ | |
| Password reset | ✅ | ✅ | ✅ | |
| Onboarding wizard | ✅ | ✅ | — | 3-step flow |
| Location sync (GMB) | ✅ | ✅ | ✅ | |
| Review sync (GMB) | ✅ | ✅ | ✅ | |
| AI response generation | ✅ | ✅ | ✅ | Groq llama-3.3-70b |
| Manual response editing | ✅ | ✅ | ✅ | |
| Publish to GMB | ✅ | ✅ | ✅ | |
| Auto-publish on generate | ✅ | ✅ | ✅ | |
| CSV export | ✅ | ✅ | Partial | Pro+ gate |
| Analytics overview | ✅ | ✅ | ✅ | Pro+ gate |
| AI Business Intelligence Report | ✅ | ✅ | ✅ 99% | PDF + JSON, Pro+ |
| Intelligence Report caching (6h) | ✅ | — | ✅ | |
| Daily report cap (Pro=4, Agency=8) | ✅ | — | ✅ | |
| Review collection links (QR/NFC) | ✅ | ? | ✅ | No frontend UI found |
| Stripe checkout | ✅ | ✅ | ✅ | Price IDs not configured |
| Stripe portal | ✅ | ✅ | ✅ | |
| Stripe webhooks | ✅ | — | ✅ | Idempotency tested |
| Telegram notifications | ✅ | ✅ | ✅ | Per-user chat_id |
| Email notifications (Resend) | ✅ | — | Partial | Fallback if no Telegram |
| Trial expiration banners | — | ✅ | — | |
| Upgrade modal | — | ✅ | — | |
| Usage limit enforcement | ✅ | — | ✅ | 402 → billing redirect |
| Per-plan rate limiting (sliding window) | ✅ | — | ✅ | In-memory only |
| Admin panel | ✅ | — | ✅ | No frontend admin UI |
| Priority score on reviews | ✅ | ✅ | — | Urgent filter (score ≥ 7) |
| Multi-language UI | — | ✅ | — | 6 locales via next-intl |
| Prompt injection sanitization | ✅ | — | — | `_sanitize_review_text()` |

---

## 5. Confirmed Bugs

### BUG-001 — CRITICAL: Google OAuth login is completely broken
**File:** `frontend/app/auth/callback/page.tsx:14`  
**What happens:** After Google OAuth, the backend sets the JWT as an HttpOnly cookie and redirects to `/auth/callback`. The frontend callback page calls `searchParams.get("token")` expecting the token in the URL query string. The token is never in the URL — it's in the cookie. Result: `token` is always `null`, the page immediately redirects to `/login`, and Google sign-in never completes.  
**Fix:** Either (a) have the backend append `?token=<jwt>` to the redirect URL, or (b) have the frontend exchange the cookie for a token via a dedicated endpoint. Option (a) is simpler but changes the cookie-based approach; option (b) maintains HttpOnly security.

### BUG-002 — Location limit not enforced correctly
**File:** `backend/app/routers/locations.py:74`  
**Code:** `max_locations = plan.features.get("max_locations", 1)`  
**What happens:** `max_locations` is a first-class column on the `Plan` model (`plan.max_locations`), not a key in the JSONB `features` dict. The `features` dict contains `auto_respond`, `telegram`, `analytics`, `export_csv`, `white_label`, `priority_support` — not `max_locations`. So `plan.features.get("max_locations", 1)` always returns `1` as a fallback. Every paid user is limited to 1 location regardless of plan.  
**Fix:** Change to `max_locations = plan.max_locations`.

### BUG-003 — Test conftest seeds Pro plan with unlimited responses; production has cap of 500
**File:** `backend/tests/conftest.py:66`  
**What happens:** `conftest.py` seeds Pro with `max_responses_per_month=0` (unlimited). Migration `013` sets it to 500 in production. Tests that check usage limits against Pro plan will not catch the real 500-cap behavior.  
**Fix:** Update `conftest.py` Pro plan to use `max_responses_per_month=500`.

### BUG-004 — In-memory sliding-window rate limiter breaks with multiple workers
**File:** `backend/app/routers/responses.py:35`  
**What happens:** `_rate_windows` is a module-level `defaultdict`. Production runs with `--workers 2` (prod compose). Each worker process has its own `_rate_windows`, so the effective rate limit is `max_calls * num_workers`. A Pro user gets 40 req/min instead of 20.  
**Fix:** Replace with Redis-backed rate limiting (e.g., redis-py with a sliding window counter), or use a single worker with async concurrency.

### BUG-005 — `GET /auth/me` is a placeholder
**File:** `backend/app/routers/auth.py` (auth router `GET /auth/me`)  
**What happens:** This endpoint returns a static string message, not user data. The working profile endpoint is `GET /users/me`. The placeholder could confuse API consumers or break if something calls `/auth/me` expecting a JSON user object.  
**Fix:** Either implement it (delegate to `GET /users/me`) or remove it.

### BUG-006 — `migration 007` sets Pro `max_responses_per_month=0` (unlimited), then 013 sets it to 500
**Files:** `007_update_plan_prices.py`, `013_abuse_protection.py`  
**What happens:** Migration 007 `UPDATE plans SET max_responses_per_month=0 WHERE id='pro'` and migration 013 only runs `UPDATE ... WHERE max_responses_per_month = 0`. This chain is correct, but the seed in `002_add_plans_subscriptions.py` also sets it to 0, so fresh installs will need 013 to run. Running migrations out of order or on a DB with custom data may fail silently.  
**Severity:** Low — only affects non-standard migration paths.

---

## 6. Security Issues

### SEC-001 — JWT stored in localStorage (XSS risk)
**File:** `frontend/lib/auth.ts:8`  
**Detail:** `localStorage.setItem(TOKEN_KEY, token)` — JWTs stored in localStorage are readable by any JavaScript running on the page. An XSS vulnerability anywhere in the app would allow token theft. The backend already sets HttpOnly cookies for Google OAuth, but the frontend ignores them and stores tokens in localStorage instead.  
**Risk:** High if any XSS vector exists. Medium otherwise.  
**Recommendation:** Migrate to HttpOnly cookies for all auth paths.

### SEC-002 — `stripe_price_id` is empty in all plan seeds
**File:** `backend/alembic/versions/002_add_plans_subscriptions.py:27`  
**Detail:** All three plans have `"stripe_price_id": ""`. Stripe checkout creates sessions using `price_id`. If billing_service uses the seeded value and it's empty, checkout sessions will fail. This is likely overridden by an env var or admin setup, but there's no validation.  
**Risk:** Revenue loss if not configured before launch.

### SEC-003 — `TOKEN_ENCRYPTION_KEY` is optional; tokens stored in plaintext if absent
**File:** `backend/app/core/crypto.py`, `backend/app/config.py`  
**Detail:** If `TOKEN_ENCRYPTION_KEY` env var is not set, Google OAuth tokens (access_token, refresh_token) are stored as plain text in the DB. A DB breach exposes all Google tokens.  
**Recommendation:** Make `TOKEN_ENCRYPTION_KEY` required in production, or document the risk prominently.

### SEC-004 — `google_maps_url` validation only checks `https://` prefix
**File:** `backend/app/routers/collection.py:59`  
**Detail:** `if not body.google_maps_url.startswith("https://")` — accepts any HTTPS URL. A user could register a collection link that redirects happy customers to a phishing site. Should validate that the URL is actually a Google Maps URL (`maps.google.com` / `g.page` / etc.).

### SEC-005 — Mock login endpoint (`/auth/mock-login`) reachable in any `ENVIRONMENT`
**Detail:** The mock login endpoint creates a JWT for `test@test.com`. If there is no environment guard, it would be accessible in production. Review whether this is blocked by `settings.ENVIRONMENT`.

### SEC-006 — No rate limiting on `/auth/register` and `/auth/login`
**Detail:** The global SlowAPI middleware is configured, but `auth.py` register and login endpoints have no `@limiter.limit(...)` decorators. Brute-force or account-creation spam is not throttled at the endpoint level.

---

## 7. Test Coverage Analysis

### Test files and scope
| File | Focus | Approx. tests |
|---|---|---|
| `test_auth.py` | Registration, login, OAuth, Telegram webhook | 14 |
| `test_reviews.py` | Listing, filters, status update, sync | ~12 |
| `test_locations.py` | Sync, deduplication, limit enforcement | ~8 |
| `test_responses.py` | Generate, edit, publish, auto-publish | ~10 |
| `test_billing.py` | Checkout, portal, webhook handling | ~12 |
| `test_webhook_idempotency.py` | Duplicate delivery, missing signature | ~6 |
| `test_billing_service.py` | Billing service unit tests | ~8 |
| `test_usage_limit.py` | Trial/plan limits, double-log regression | ~8 |
| `test_abuse_protection.py` | Daily report cap, sliding window | ~8 |
| `test_analytics.py` | Overview, intelligence report, cache, PDF | 19 (99% coverage) |
| `test_collection.py` | QR links, feedback routing | ~8 |
| `test_gmb_service.py` | Token refresh, review sync, pagination | ~10 |
| `test_rate_limiting.py` | SlowAPI wiring, 429 behavior | ~5 |
| `test_health.py` | Health endpoint | ~2 |
| `test_admin.py` | Admin CRUD, access control | ~10 |

### Coverage notes
- `analytics.py` — **99%** (1 uncovered line: the `len(locations) > 1` branch label)
- `responses.py` — well covered via direct-call tests
- **No frontend tests** — zero test files in `frontend/`
- Auth callback flow (BUG-001) has no integration test covering the full OAuth redirect chain
- `locations.py` `sync_locations` tests pass but cover a code path that contains BUG-002 — the wrong `features.get("max_locations")` call is never caught by the test because the mock plan's features dict also doesn't have that key, so the default of `1` silently applies

### Infrastructure
- Test runner: pytest-asyncio, real PostgreSQL (`reviewdb_test`)
- Isolation: per-test transaction rollback via connection-level savepoints
- Known issue: async coverage tracing with ASGI transport → solved by calling route handlers directly

---

## 8. Environment Variables

### Required (backend will fail to start without these)
| Variable | Notes |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg://...` |
| `GOOGLE_CLIENT_ID` | Google OAuth app credential |
| `GOOGLE_CLIENT_SECRET` | Google OAuth app credential |
| `GOOGLE_REDIRECT_URI` | Must match OAuth console (`https://domain.com/auth/callback`) |
| `GROQ_API_KEY` | LLM for response generation and intelligence reports |
| `SECRET_KEY` | JWT signing, minimum 32 chars |

### Required for production revenue
| Variable | Notes |
|---|---|
| `STRIPE_SECRET_KEY` | Billing checkout and portal |
| `STRIPE_WEBHOOK_SECRET` | Webhook signature verification |
| `STRIPE_PRICE_IDS` | Must be set per-plan; currently empty strings in DB |

### Optional but strongly recommended
| Variable | Default | Notes |
|---|---|---|
| `TOKEN_ENCRYPTION_KEY` | `""` (plaintext) | Fernet key for encrypting OAuth tokens in DB |
| `TELEGRAM_BOT_TOKEN` | `""` | Notifications disabled without this |
| `RESEND_API_KEY` | `""` | Email disabled without this |
| `SENTRY_DSN` | `None` | Error tracking |
| `FRONTEND_URL` | — | Used in email links |

### Frontend (Next.js)
| Variable | Notes |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend URL, defaults to `http://localhost:8000` |

### Missing from `.env.example`
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID_*`
- `TOKEN_ENCRYPTION_KEY`
- `RESEND_API_KEY`
- `AUTO_VERIFY_EMAIL` (exists in config but not in example)
- `NEXT_PUBLIC_API_URL` (frontend env var not documented)

---

## 9. Deployment Readiness

### Infrastructure (`docker-compose.prod.yml`)
- ✅ PostgreSQL 16, persistent volume
- ✅ Backend: `alembic upgrade head && uvicorn --workers 2` on startup
- ✅ nginx: port 80+443, Let's Encrypt via certbot sidecar with auto-renew
- ✅ Internal Docker network (backend and frontend not directly exposed)
- ✅ Health check on backend (`/health`)
- ⚠️ Backend uses 2 workers — incompatible with in-memory rate limiter (BUG-004)
- ⚠️ `.env.prod` file required but not in repo and not documented beyond its reference
- ⚠️ `nginx/nginx.conf` referenced but not audited (file not in repo root)
- ❌ `DOMAIN` env var required for nginx config template but not in `.env.example`

### Manual post-deploy steps (from CLAUDE.md)
1. Register Stripe webhook: `stripe listen --forward-to https://domain.com/billing/webhook`
2. Register Telegram webhook: POST to `api.telegram.org/bot<TOKEN>/setWebhook`
3. Set all env vars in `.env.prod`

### Startup behavior
- `Base.metadata.create_all` runs on every app startup (lifespan handler in `main.py`) **and** `alembic upgrade head` runs in prod compose. This is harmless (create_all is idempotent) but inconsistent — alembic should be the single source of truth for schema state.

---

## 10. What's Missing Before Launch

### Blockers (launch is broken without these)
1. **Fix BUG-001 (Google OAuth):** Google login returns users to `/login` immediately. For any user who signs in with Google, the product is inaccessible.
2. **Fix BUG-002 (location limit):** Paid Starter and Pro users are hard-limited to 1 location (wrong default). Agency users pay for 10 locations but can only sync 1.
3. **Configure Stripe price IDs:** All plan rows have empty `stripe_price_id`. Checkout will fail unless price IDs are inserted or the billing service sources them from env vars.
4. **Create `.env.prod`:** The production compose file requires this file. There is no template for it (`.env.example` is incomplete).

### High priority (poor UX or revenue risk)
5. **Add nginx.conf:** The prod nginx config template is referenced in docker-compose but not present in the audited files.
6. **Database indexes:** `reviews` table has no index on `(location_id, review_date)` or `status`. With thousands of reviews per user, analytics and listing queries will be slow.
7. **Fix conftest Pro plan** (BUG-003): Tests don't cover the real 500-response cap for Pro.
8. **Frontend admin UI:** The admin backend (stats, user management, cost monitor) has no frontend. Admins must use the API directly.

### Medium priority
9. **Frontend tests:** Zero test coverage on any frontend component.
10. **Fix multi-worker rate limiter** (BUG-004): Replace `_rate_windows` in-memory dict with Redis.
11. **No review collection link UI:** The backend for QR/NFC review funnels is fully implemented and tested, but there's no frontend page to create or manage collection links.
12. **`response_instructions` length limit:** Users can store arbitrarily long instructions; no database column length cap and no API validation.
13. **`/auth/me` placeholder:** Remove or implement (BUG-005).
14. **Resend / email templates:** Email notifications are wired but templates not audited — welcome email, reset email, and verification email content unknown.

### Low priority
15. **Auth rate limiting:** Add `@limiter.limit("5/minute")` to `/auth/register` and `/auth/login`.
16. **`google_maps_url` validation:** Restrict to actual Google Maps URLs (SEC-004).
17. **Remove `create_all` from lifespan:** Let Alembic own schema exclusively.
18. **`TOKEN_ENCRYPTION_KEY` documentation:** Add to `.env.example` with generation instructions.

---

## 11. Code Quality Notes

### Strengths
- **Clean separation of concerns:** routers → services → models. No business logic leaks into route handlers beyond orchestration.
- **Async throughout:** SQLAlchemy async, httpx async, all route handlers async. No sync blocking calls.
- **Feature-gate pattern:** `require_plan_feature("analytics")` dependency is reusable and consistent across all Pro-gated endpoints.
- **Prompt injection sanitization:** `_sanitize_review_text()` strips control characters and truncates before sending to LLM.
- **Idempotent migrations:** Migrations 011–013 check for existing columns/tables before creating them — safe to re-run.
- **Transactional test isolation:** Per-test connection rollback gives clean state without truncating tables.
- **99% analytics coverage:** Direct-handler test pattern cleanly bypasses ASGI coverage tracing issues.
- **LLM fallback:** `generate_intelligence_report` falls back to `_minimal_fallback()` on JSON parse errors — report never crashes.

### Weaknesses
- **Denormalized `users.plan` column:** `User.plan` (a String column) exists alongside `subscriptions.plan_id`. These can diverge. The plan column appears to be a legacy field; the subscription is the source of truth but both exist.
- **`locations.py` reads `plan.features` for max_locations:** As noted in BUG-002, accessing a plan column via JSONB features key is incorrect and untested.
- **No pagination on analytics:** `reviews_by_day` query in analytics overview fetches up to 30 rows unbounded; the `_fetch_reviews` for intelligence reports fetches all matching reviews in memory. For high-volume accounts this could be large.
- **SlowAPI in-memory storage:** `limiter = Limiter(storage_uri="memory://")` — same problem as the sliding window: state is per-process, not shared across workers.
- **`admin.py` LIKE search not parameterized:** Uses `ilike(f"%{search}%")` directly. SQLAlchemy parameterizes bound values so SQL injection is prevented, but there's no escape of `%` and `_` wildcard characters — a search for `%` would match all users.
- **`auth/me` returns a string:** A GET endpoint named `/auth/me` returning `{"message": "Use /users/me for profile data"}` is a footgun for API consumers.
- **Frontend `api.ts` calls `/api/telegram-status` and `/api/test-telegram`:** These are Next.js API routes. No `frontend/app/api/telegram-status/route.ts` or similar file was found. If these routes don't exist, the settings page Telegram features will produce 404 errors. (The actual data comes from `GET /users/me/telegram-status` on the backend, which is correct — the Next.js proxy routes are the unknown.)
- **`_save_cached_report` never prunes old entries:** Old expired `analytics_cache` rows accumulate. The daily cap counter includes them (by design), but the table will grow unboundedly. A nightly cleanup job or TTL-based deletion is missing.
- **Groq client instantiated per request:** In `analytics.py:_build_report`, `AsyncGroq(api_key=...)` is created on every cache miss. Should be a module-level singleton or dependency.
