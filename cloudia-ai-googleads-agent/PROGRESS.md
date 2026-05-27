# PROGRESS.md

# Google Ads Agent System — Session Handoff File

# READ THIS BEFORE WRITING A SINGLE LINE OF CODE

-----

## Last Updated

2026-05-24T00:00:00Z by claude-sonnet-4-6

## Current Phase

Phase 10 — COMPLETE. All phases done. Frontend dashboard added.

## Completed Items

- [x] Project folder structure created
- [x] requirements.txt populated
- [x] .env.example created
- [x] config.py with all constants
- [x] db/models.py — all 5 models defined (Account, CampaignSnapshot, AuditLog, ApprovalQueue, IndustryBenchmark, AgentRun)
- [x] db/session.py — session factory
- [x] Alembic configured — alembic.ini, db/migrations/env.py, db/migrations/script.py.mako, db/migrations/versions/0001_initial_schema.py
- [x] README.md — setup instructions
- [x] google_ads/client.py — AdsClient wrapper
- [x] google_ads/queries.py — all GAQL constants
- [x] google_ads/executor.py — full execution logic with all action handlers
- [x] google_ads/campaign_builder.py — full campaign structure creation (budget → campaign → ad groups → keywords → ads)
- [x] ai/claude.py — ClaudeClient wrapper with complete() and complete_json()
- [x] ai/context_builder.py — build_client_context() per spec
- [x] ai/prompts/auditor.py — system prompt
- [x] ai/prompts/manager.py — system prompt
- [x] ai/prompts/reporter.py — system prompt
- [x] ai/prompts/keyword_scout.py — system prompt
- [x] ai/prompts/creator.py — system prompt
- [x] agents/base.py — BaseAgent with run logging, calibration check, error capture
- [x] agents/auditor.py — full implementation with _detect_anomalies() pure function
- [x] db/snapshots.py — snapshot read/write + parse_gaql_row()
- [x] notifications/email.py — SMTP: send_email, send_alert, send_queue_summary, send_weekly_report
- [x] agents/reporter.py — full implementation
- [x] agents/manager.py — full implementation with custom_rules validation
- [x] db/queue.py — write_queue_item, get_pending_items, approve_item, reject_item, get_item_by_id
- [x] agents/keyword_scout.py — full implementation
- [x] agents/creator.py — full implementation (create_from_brief method)
- [x] api/schemas.py — all Pydantic v2 schemas
- [x] api/routes.py — all 9 API routes
- [x] api/app.py — FastAPI app with CORS + lifespan + /health
- [x] orchestrator.py — loops all agents across all active accounts
- [x] main.py — APScheduler + uvicorn daemon thread
- [x] tests/conftest.py — all fixtures
- [x] tests/test_auditor.py — 5 tests
- [x] tests/test_context_builder.py — 5 tests
- [x] tests/test_manager.py — 4 tests
- [x] tests/test_executor.py — 3 tests (tests db/queue.py functions)
- [x] docs/ARCHITECTURE.md
- [x] docs/AGENT_SPECS.md
- [x] docs/DATABASE.md
- [x] docs/ONBOARDING.md
- [x] docs/DECISIONS.md

## Decisions Made This Session

- ADR-001: Single process (APScheduler + FastAPI daemon thread). No message queue. See docs/DECISIONS.md.
- ADR-002: All Google Ads + Claude calls go through wrapper classes only.
- ADR-003: Calibration check skips agents; Auditor still saves snapshots.
- ADR-004: Approval queue is the sole write gate — nothing executes without approval.
- ADR-005: Costs stored in micros, converted to ZAR at display/prompt time.
- ADR-006: Creator agent always creates campaigns in PAUSED state.
- ADR-007: ClaudeClient.complete_json() strips markdown fences before json.loads().
- ADR-008: Orchestrator isolates per-account exceptions so one failure never stops the loop.

## Frontend Dashboard (added after Phase 10)

14 files in `google_ads_agents/frontend/`:
- `index.html` — app shell
- `css/style.css` — full design system (1,758 lines)
- `js/config.js` — workforce registry (add new workforces here)
- `js/api.js` — centralized fetch wrapper
- `js/app.js` — hash router + `window.navigate()`
- `js/components/` — sidebar (with pending badge), toast, modal
- `js/views/` — dashboard, queue (approve/reject/execute), audit, accounts, creator, runs

Served by FastAPI at `http://localhost:8000/app/` (StaticFiles mount).
Root `/` redirects to `index.html`.

Adding a new workforce: add one entry to `WORKFORCES` array in `js/config.js`.

## Blockers / Open Questions

- **Google Ads API credentials**: Copy .env.example to .env and fill in all GOOGLE_ADS_* values before running. Developer token must have Standard or Basic access for live accounts.
- **PostgreSQL**: Create the database with `createdb google_ads_agents` then run `alembic upgrade head`.
- **Baselines**: Must be set manually via `POST /accounts/{id}/baseline` after 30 days of calibration data. Use `db/snapshots.py` queries to derive the values.
- **Industry benchmarks table**: Empty on first run. Seed it with real benchmark data (Wordstream or internal) for Claude to have comparative data.

## Files Modified This Session

All files — initial build from scratch.

## Next Session Should Start With

The system is fully built. Next steps are operational:

1. Copy `.env.example` to `.env` and fill in all values
2. Run `createdb google_ads_agents`
3. Run `alembic upgrade head` to create all tables
4. Seed `industry_benchmarks` table with data for your client industries
5. Insert the first client account via the SQL in `docs/ONBOARDING.md`
6. Run `python main.py` to start the scheduler + API
7. After 30 days of calibration, set baselines via `POST /accounts/{id}/baseline` and set status to `active`

If extending the system, see `docs/DECISIONS.md` before deviating from the architecture.
