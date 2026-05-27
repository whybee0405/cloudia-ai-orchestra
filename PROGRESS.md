# CloudIA AI Orchestra — Progress Tracker

Last updated: 2026-05-27

---

## Phase 1 — Brand DNA Service (Foundation)
> Must be complete before any other phase. All other services depend on the client_id and brand context this service provides.

- [ ] Scaffold `cloudia-ai-brand-dna-service/` directory and project structure
- [ ] FastAPI app + Alembic + SQLAlchemy setup
- [ ] Database models: `Client`, `BrandDNA`, `ICPPersona`
- [ ] Client CRUD endpoints (`GET/POST /api/clients`, `GET/PATCH /api/clients/{id}`)
- [ ] Brand DNA endpoints (`GET/PUT /api/clients/{id}/brand-dna`)
- [ ] Persona endpoints (`GET/POST /api/clients/{id}/personas`, `PATCH/DELETE /api/clients/{id}/personas/{pid}`)
- [ ] Industry persona template endpoint (`GET /api/clients/{id}/personas/templates`)
- [ ] Internal brand context endpoint (`GET /internal/clients/{id}/brand-context`)
- [ ] Brand DNA Enrichment Agent (Claude, website scrape → suggestions)
- [ ] `POST /api/clients/{id}/brand-dna/enrich` endpoint
- [ ] Master Director Agent (cross-service state fetch + Claude suggestions)
- [ ] `GET /api/clients/{id}/suggestions` endpoint
- [ ] `GET /internal/health` endpoint
- [ ] Docker setup (`Dockerfile`, `.env.example`)
- [ ] Alembic initial migration

---

## Phase 2 — Combined Frontend Skeleton
> Routing, layout, and Brand DNA wizard. No service-specific modules yet.

- [ ] Scaffold `cloudia-ai-frontend/` (Vite + React 18 + TypeScript + TailwindCSS)
- [ ] Install dependencies: React Query, React Router v6, Zustand
- [ ] App shell: sidebar navigation, header, layout
- [ ] Client list page (`/clients`)
- [ ] Create client page (`/clients/new`)
- [ ] Client Hub page (`/clients/:id`) — layout only, placeholder cards
- [ ] Brand DNA API client (`src/api/brand-dna.ts`)
- [ ] Brand DNA Wizard — Step 1: Business Basics
- [ ] Brand DNA Wizard — Step 2: Brand Voice
- [ ] Brand DNA Wizard — Step 3: Visual Identity
- [ ] Brand DNA Wizard — Step 4: Key Messages
- [ ] Brand DNA Wizard — Step 5: ICP Persona Builder
- [ ] Brand DNA Wizard — Step 6: Review + Enrich
- [ ] Brand DNA view/edit page (`/clients/:id/brand-dna`)
- [ ] `<BrandDNABadge />` shared component
- [ ] `<SuggestionCard />` shared component
- [ ] Director Suggestions panel in Client Hub
- [ ] Docker setup for frontend

---

## Phase 3 — Brand DNA Injection (All 3 Backends)
> Wire brand context into every agent prompt. Do not start service-specific frontend modules until this is done.

- [ ] Brand DNA HTTP client utility (shared pattern for all backends)
- [ ] **Campaign Director**: add `brand_dna_client_id` UUID column (Alembic migration)
- [ ] **Campaign Director**: inject brand context into `BaseAgent`
- [ ] **Campaign Director**: add `GET /api/campaigns/clients/{client_id}/summary`
- [ ] **Campaign Director**: add `GET /internal/health`
- [ ] **Google Ads**: add `brand_dna_client_id` UUID column (Alembic migration)
- [ ] **Google Ads**: inject brand context into `BaseAgent` (Creator + Reporter agents)
- [ ] **Google Ads**: add `GET /api/ads/clients/{client_id}/summary`
- [ ] **Google Ads**: add `GET /internal/health`
- [ ] **WebDev**: add `brand_dna_client_id` UUID column (Alembic migration)
- [ ] **WebDev**: inject brand context into `ContentAgent`, `SEOAgent` (ICP keywords), `MediaAgent` (visual style)
- [ ] **WebDev**: add `GET /api/webdev/clients/{client_id}/summary`
- [ ] **WebDev**: add `GET /internal/health`

---

## Phase 4 — Frontend: Campaign Director Module
> Port Campaign Director UI into unified frontend under `/clients/:id/campaigns`.

- [ ] Campaign Director API client (`src/api/campaigns.ts`)
- [ ] Campaign list view within Client Hub
- [ ] Create campaign form
- [ ] Campaign detail page (pipeline view)
- [ ] `<PipelineVisualiser />` shared component (reused by WebDev too)
- [ ] `<ApprovalGateCard />` shared component
- [ ] Content calendar view
- [ ] Asset viewer (images, videos, copy)
- [ ] WebSocket real-time pipeline updates
- [ ] Analytics view

---

## Phase 5 — Frontend: Google Ads Module
> Port Google Ads UI into unified frontend under `/clients/:id/ads`.

- [ ] Google Ads API client (`src/api/google-ads.ts`)
- [ ] Ads account list / link account
- [ ] Approval queue list + approve/reject/execute actions
- [ ] `<ApprovalQueueItem />` shared component
- [ ] Audit log view
- [ ] Campaign creator form (on-demand Creator agent)
- [ ] Weekly report view

---

## Phase 6 — Frontend: WebDev Module
> Port WebDev UI into unified frontend under `/clients/:id/webdev`.

- [ ] WebDev API client (`src/api/webdev.ts`)
- [ ] Project list within Client Hub
- [ ] Create project form (WordPress vs Shopify choice)
- [ ] Project detail page (pipeline view — reuse `<PipelineVisualiser />`)
- [ ] Content approval gate (reuse `<ApprovalGateCard />`)
- [ ] Site review gate
- [ ] WebSocket real-time pipeline updates

---

## Phase 7 — Director Suggestions + Cross-Service Integration

- [ ] Director Agent: fetch summaries from all 3 backends
- [ ] Director Agent: Claude prompt for cross-service analysis
- [ ] Suggestion ranking logic (priority scoring)
- [ ] Suggestion cards wired to action URLs in frontend
- [ ] `<TokenCostBadge />` shared component (visible in agent task views)
- [ ] Unified cost dashboard (optional — total spend across all agents per client)

---

## Phase 8 — Root Docker Compose + Deployment

- [ ] Root `docker-compose.yml` (all 5 services + 4 postgres DBs + redis + nginx)
- [ ] nginx config (`nginx/cloudia.conf`)
- [ ] Root `.env.example` with all required variables
- [ ] `docker-compose.prod.yml` with SSL via Certbot
- [ ] Deployment runbook in `DEPLOY.md`
- [ ] Remove old standalone frontends from Campaign Director + WebDev + Google Ads

---

## Deferred / Future Phases

- [ ] **Brand DNA — spec and build properly** (user note: "we can spec this out properly later" — personas and visual identity are MVP, deeper brand strategy layer TBD)
- [ ] Client-facing approval portal (view-only + approval for external clients)
- [ ] Cost/token reporting dashboard across all services
- [ ] Unified notification system (email/Slack on approval gates, anomaly alerts)
- [ ] Role-based access control (account manager vs. strategist vs. admin)
- [ ] Multi-agency / white-label support

---

## Current Status

| Phase | Status | Notes |
|-------|--------|-------|
| Architecture + Planning | ✅ Complete | MASTER_ARCHITECTURE.md + MASTER_PROMPT.md written |
| Phase 1 — Brand DNA Service | ⬜ Not started | |
| Phase 2 — Frontend Skeleton | ⬜ Not started | |
| Phase 3 — Brand DNA Injection | ⬜ Not started | |
| Phase 4 — Campaigns Module | ⬜ Not started | |
| Phase 5 — Google Ads Module | ⬜ Not started | |
| Phase 6 — WebDev Module | ⬜ Not started | |
| Phase 7 — Director Suggestions | ⬜ Not started | |
| Phase 8 — Deployment | ⬜ Not started | |
