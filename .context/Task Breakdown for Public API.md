# Task Breakdown for Public API

**TASK DECOMPOSITION – Public API (Phase 3 / Component = LLD-PublicAPI-v1)**

---

### **Task Set Overview**

- **Component:** Public API (FastAPI on Cloud Run)
- **LLD Reference:** `LLD-PublicAPI-v1` @ commit `5c8e6ab`
- **Goal:** Deliver a production-ready service that satisfies every requirement in the approved LLD, complete with CI/CD, tests and basic observability.

---

### **Ticket Table**

| ID | Title | Description (what & why) | Target Files / Paths | Implementation Steps (ordered) | Acceptance Criteria (testable) | Dependencies | Est. | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **API-BASE-001** | Bootstrap FastAPI project | Provide a runnable project skeleton for team productivity. | `/api/main.py`, `pyproject.toml`, `docker/` | 1. Init Poetry project.2. Add FastAPI, Uvicorn.3. Create `main.py` with health route `/ping`.4. Dev Dockerfile + docker-compose for hot-reload.5. README quick-start. | `curl localhost:8000/ping` → `{"pong":true}`.Code passes `ruff -A` & `mypy --strict`. | — | S | **P0** |
| **API-BASE-002** | IaC + Cloud Run deploy | Turn skeleton into a reachable staging service. | `/infra/*.tf`, `.github/workflows/deploy.yml` | 1. Terraform for Cloud Run svc, SA, Secret Mgr.2. Build & push container (`gcloud` or Cloud Build).3. Add deploy job in GitHub Actions. | `curl $STG_URL/ping` → 200.Terraform plan is idempotent.CI green on merge. | BASE-001 | M | **P0** |
| **API-AUTH-003** | Supabase Auth middleware | Enforce authenticated user context on protected routes. | `/api/services/auth.py`, `tests/test_auth.py` | 1. Fetch JWKS at startup & cache.2. `verify_jwt` util with PyJWT.3. FastAPI dependency `get_current_user`.4. 401/403 handlers. | Unit tests: valid/invalid JWT paths.Route `/me` returns 401 w/out token. | BASE-001 | S | **P0** |
| **API-DB-004** | Supabase Postgres wrapper | Async DB access with connection pooling & RLS. | `/api/services/supabase.py` | 1. Create `asyncpg` pool in lifespan.2. Helper `fetch_one`, `execute`.3. Set `request.jwt.claims.sub` for RLS each txn.4. Unit test simple insert/select. | Pool closes on shutdown.Supabase local test passes. | AUTH-003 | M | **P0** |
| **API-DB-005** | Sqitch migration set `01_init` | Create schema from LLD in staging DB. | `/db/sqitch/**` | 1. Author SQL for tables, indices, RLS policies.2. GitHub Action step `sqitch deploy`.3. Docs on running locally. | `sqitch verify` passes in CI.Tables visible in Supabase studio. | DB-004 | M | **P0** |
| **API-ROUTE-006** | `/auth/token` endpoint | Exchange OAuth code for Supabase session; return JWT. | `/api/routes/auth.py` | 1. POST handler.2. Call Supabase `/token?grant_type=pkce`.3. Store/update user profile row. | 200 JSON with `jwt`, `user.email`.401 on bad code. | AUTH-003 | S | **P0** |
| **API-ROUTE-007** | `/me` endpoint | Return authenticated user profile. | `/api/routes/auth.py` | Simple SELECT from `users` table. | 200 JSON; 401 if unauth. | AUTH-003, DB-004 | S | **P0** |
| **API-ROUTE-008** | `/clips` POST (link ingest) | Idempotent save of link + publish `clip.created`. | `/api/routes/clips.py` | 1. Validate URL regex.2. DB `INSERT ... ON CONFLICT` into `clips`.3. Insert into `user_clips`.4. Publish Pub/Sub if new clip.5. Return 201. | First save: 201 + `queued`.Second save by same user: 409.Pub/Sub message visible. | DB-004, PUB-013 | M | **P0** |
| **API-ROUTE-009** | `/clips/{id}` GET | Fetch clip + tags + `saved_at` for caller. | `/api/routes/clips.py` | SQL join per LLD. | 200 JSON correct; 404 if no access. | DB-004 | S | **P0** |
| **API-ROUTE-010** | `/search` GET | Keyword & tag search via FTS. | `/api/routes/search.py` | 1. Parse `q` param.2. Execute FTS query.3. Paginate 40. | P95 latency < 300 ms on 10 k rows.Returns expected matches in tests. | DB-004, DB-005 | M | **P0** |
| **API-ROUTE-011** | Collections CRUD | Manage user collections & membership. | `/api/routes/collections.py` | Implement create, patch, add/remove clip per LLD. | Full happy-path integration tests pass. | DB-004 | M | P1 |
| **API-ROUTE-012** | Digest preference endpoints | Preview email & subscribe cadence. | `/api/routes/digest.py` | 1. Dummy HTML preview using latest 3 clips.2. Save cadence in `users.prefs`. | 200 preview returns HTML.POST stores cadence. | DB-004 | S | P1 |
| **API-PUB-013** | Pub/Sub publisher module | Reliable event emission. | `/api/services/pubsub.py` | 1. Async publisher with retry policy.2. DLQ on failure. | `clip.created` shows in topic (verified by test script). | IaC-002 | S | **P0** |
| **API-OBS-014** | Observability hooks | Logs, metrics, tracing for SRE. | `/api/middleware/otel.py`, `logging.json` | 1. Add OTEL SDK auto-instrument.2. JSON structured logs.3. Custom latency histogram. | Trace spans visible in Cloud Trace.Error logs structured. | BASE-001 | S | P1 |
| **API-TEST-015** | Contract + integration test suite | CI safety-net for all endpoints. | `/tests/**`, `.env.test` | 1. Schemathesis autogen from OpenAPI.2. Spin-up Supabase test container.3. Coverage report. | CI passes; coverage ≥ 80 %. | All prior routes | M | **P0** |
| **API-CI-016** | Full CI/CD pipeline | Ensure code quality & automated deploys. | `.github/workflows/api.yml` | 1. Lint (Ruff).2. Type check (MyPy).3. Tests.4. Build image.5. Deploy Terraform.6. Notify Slack. | Green on `main` merge.Deployment URL posted to Slack. | TEST-015, IaC-002 | M | **P0** |
| **API-DOC-017** | API Documentation polish | First-class Swagger & README usage examples. | `/api/main.py`, `docs/` | 1. Add OpenAPI meta tags.2. Terraform outputs doc URL.3. README snippet for each endpoint. | `/docs` renders with auth flow sample.README passes `markdown-lint`. | All routes | S | P2 |
| **API-SEC-018** | Security headers & HSTS | Baseline web-hardening. | `/api/middleware/security.py` | 1. Add middleware for HSTS, X-Content-Type-Options.2. CSP basic (`frame-ancestors 'none'`). | Headers visible in staging via `curl -I`. | BASE-001 | S | P2 |

**Complexity Legend:** S = ≤½ day, M = 1-2 days, L ≥ 3 days

**Priority Legend:** P0 = must-have for MVP, P1 = nice-to-have before beta, P2 = polish

---

### **Suggested Parallelization Plan**

| Stream A (Infra/Auth/DB) | Stream B (Core Routes) | Stream C (Observability + Docs) |
| --- | --- | --- |
| BASE-001 → BASE-002 → AUTH-003 → DB-004 → DB-005 | PUB-013 → ROUTE-008 → ROUTE-009 → ROUTE-010 → ROUTE-011 → ROUTE-012 | OBS-014 → TEST-015 → CI-016 → SEC-018 → DOC-017 |

*Streams are mostly independent after DB-005 completes; FE can integrate once ROUTE-008/009 are live.*

---

### **Validation Checklist (for final QA sign-off)**

1. **Smoke / Ping** – `GET /ping` returns 200 in staging & prod.
2. **Auth Flow** – Valid Google token → 200 `/me`; invalid → 401.
3. **Ingest** – First save of a link publishes `clip.created`; second save returns 409.
4. **Search** – Keyword present in transcript appears in `/search` within ≤ 30 s of ingest (after AI worker).
5. **RLS** – User A cannot fetch User B’s clip via `/clips/{id}` (returns 404).
6. **CI/CD** – `main` branch merge triggers lint, tests, build, deploy pipeline – all green.
7. **Observability** – Cloud Trace shows spans; Cloud Monitoring dashboard graphs latency & 5xx rates.
8. **Infrastructure Idempotence** – Re-running Terraform yields **0 to change**.
9. **Docs** – OpenAPI `/docs` renders and includes auth sample curl.
10. **Security Headers** – Response includes `Strict-Transport-Security`, `X-Content-Type-Options`.

---

**Awaiting: (Approve Tasks for Public API | Feedback)**