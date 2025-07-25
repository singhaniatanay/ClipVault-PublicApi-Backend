# Project Memory and Context

## 🏗️ Architecture Overview
- **Framework**: FastAPI (Python 3.12)
- **Auth**: Supabase JWT, JWKS validation, RLS enforced in DB
- **Database**: Supabase Postgres, asyncpg, RLS, schema managed by Sqitch
- **Eventing**: Google Cloud Pub/Sub, DLQ for failures, event-driven AI pipeline
- **Deployment**: Cloud Run, Docker, GitHub Actions CI/CD
- **Testing**: Pytest, Hypothesis, contract tests, 99%+ coverage

## 🔑 Key Technical Decisions
- **No custom users table**: Use Supabase `auth.users` for all user data
- **Dependency Injection**: Kept simple with FastAPI `Depends`, no external DI framework
- **Idempotency**: All ingest endpoints are idempotent (upsert, ON CONFLICT)
- **Event-Driven**: All new clips trigger Pub/Sub events for AI processing
- **Observability**: Structured logging, health checks, OpenTelemetry planned
- **Extensibility**: Models and endpoints designed to support future media types and features

## 🧠 AI's Working Context
- **All core endpoints and services are implemented and tested**
- **All infrastructure (DB, Pub/Sub, Cloud Run) is set up and integrated**
- **All business logic and edge cases are now covered by tests**
- **/clips POST endpoint (API-ROUTE-008) is fully implemented, tested (unit, integration, and manual via HTML), and integrated with Supabase Auth and Pub/Sub**
- **OAuth HTML test page supports end-to-end /clips testing**
- **User feedback and requirements are incorporated in real time**

## 📚 Reference Files
- `.context/Task Breakdown for Public API.md` (task list)
- `.context/LLD Public API.md` (low-level design)
- `api/services/supabase.py`, `api/services/pubsub.py`, `api/routes/auth.py`, `api/routes/clips.py` (core logic)
- `tests/` (comprehensive test suite)
- `oauth_test.html` (manual end-to-end test page)

---

**This context is kept up-to-date as the project evolves.** 