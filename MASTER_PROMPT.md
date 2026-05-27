# CloudIA AI Orchestra — Master Prompt

## What This Is

CloudIA AI Orchestra is an internal digital marketing AI platform for a South African digital agency. It combines three AI agent workforces under a single client-centric frontend. Every agent output is tailored using a centralised Brand DNA layer that stores each client's identity, voice, visual style, and customer personas.

This document is the canonical context document for any development session. Read it before touching any part of this codebase.

---

## The Four Services

### 1. Brand DNA Service (`cloudia-ai-brand-dna-service/`) — NEW, build first
The foundation everything else depends on. Stores client records, brand identity, and ICP personas. Exposes an internal read API that all other backends call at agent start time to inject brand context into every Claude prompt.

Also hosts the Master Digital Marketing Director Agent — a cross-service suggestion engine that reads live state from all three other services and surfaces prioritised next-action recommendations on the client dashboard.

### 2. Campaign Director (`cloudia-ai-campaign-director-agent/`) — EXISTING, modify
Multi-agent social media content pipeline. 17 specialised agents handle the full lifecycle: brief → plan → copy → images → video → approval → schedule → publish → analytics. Supports 9+ platforms. Uses Celery + Redis for async task execution.

### 3. Google Ads Service (`cloudia-ai-googleads-agent/`) — EXISTING, modify
Human-in-the-loop Google Ads management. Scheduled agents (APScheduler) detect anomalies, recommend bid/budget changes, discover keywords, and generate weekly reports. Nothing executes without explicit human approval via the approval queue.

### 4. WebDev Service (`cloudia-ai-webdev-agent/`) — EXISTING, modify
Multi-agent website builder for WordPress and Shopify. Pipeline of 6-7 agents builds a complete site from a brief. Approval gates pause the pipeline for human content review and site review before publishing.

### 5. Combined Frontend (`cloudia-ai-frontend/`) — NEW
Single React/TypeScript/Vite SPA. Client-centric: you always pick a client first, then everything for that client is accessible in one hub. Replaces the three separate frontends that currently exist in the individual services.

---

## Non-Negotiable Design Rules

1. **Brand DNA is injected into every Claude prompt.** No agent should generate copy, creative direction, or SEO content without first fetching the client's brand context from the Brand DNA Service.

2. **Brand DNA Service owns the canonical `client_id`.** It is a UUID. All other services store this UUID as a foreign key. Never let individual services generate their own client IDs.

3. **Cross-service actions are suggested, never automatic.** The Director Agent recommends next actions; a human must explicitly launch them.

4. **Each backend keeps its own database.** Do not share a PostgreSQL instance across services. `client_id` UUID is the only shared identifier.

5. **Every agent tracks tokens and cost.** All `agent_tasks` / `agent_runs` records must store `input_tokens`, `output_tokens`, and `cost_usd`.

6. **Approval gates are sacred.** Never auto-approve or skip gates. Human review is a core product feature.

7. **Modular frontend.** Each service has its own `src/modules/{service}/` directory. Shared components live in `src/shared/`. No module imports directly from another module — only through `src/api/` clients and `src/shared/`.

8. **`.env` is never committed.** `.env.example` is always committed and kept up to date.

---

## Brand DNA Injection Format

Every Claude system prompt in every backend must include this block (fetched from Brand DNA Service internal API, cached 5 minutes):

```
=== BRAND DNA: {client_name} ===
Industry: {industry}
Brand Voice: {tone} — {language_style}
Personality: {personality_traits joined by ", "}
Visual Style: {visual_style} | Primary Colour: {primary_color}
USPs: {usps joined by " | "}
Key Messages: {key_messages joined by " | "}

TARGET PERSONAS:
1. {persona_name} | Age: {age_min}-{age_max}
   Pain Points: {pain_points}
   Goals: {goals}
   SEO Keywords: {seo_keywords}
   Vocabulary: {vocabulary}
[repeat for each persona, max 5]
===============================
```

Use Anthropic prompt caching on this block (mark as `cache_control: ephemeral`) to avoid re-paying for it on every turn of a long agentic task.

---

## Brand DNA Service — Build Spec

### Models
- `Client`: id (UUID), name, website_url, industry, sub_industry, location, timezone
- `BrandDNA`: FK→Client, tagline, tone, language_style, personality_traits[], primary_color, secondary_colors[], accent_color, heading_font, body_font, logo_url, visual_style, usps[], pain_points_addressed[], key_messages[], competitors[], differentiators[]
- `ICPPersona`: FK→Client, persona_name, age_min, age_max, gender_skew, income_bracket, location_type, interests[], values[], pain_points[], goals[], preferred_channels[], seo_keywords[], vocabulary[], order

### Key Endpoints
- `GET/POST /api/clients` — list + create clients
- `GET/PATCH /api/clients/{id}` — get + update client
- `GET /api/clients/{id}/brand-dna` — get brand DNA
- `PUT /api/clients/{id}/brand-dna` — save full brand DNA form
- `POST /api/clients/{id}/brand-dna/enrich` — trigger Claude enrichment agent
- `GET/POST /api/clients/{id}/personas` — list + create personas
- `GET /api/clients/{id}/personas/templates` — industry persona templates
- `GET /api/clients/{id}/suggestions` — Director Agent cross-service suggestions
- `GET /internal/clients/{id}/brand-context` — compact JSON for agent injection (internal only, not exposed via nginx)

### Enrichment Agent Behaviour
When `POST /api/clients/{id}/brand-dna/enrich` is called:
1. Fetch the saved form data
2. If website_url provided, use httpx to fetch page text (not a browser — just raw HTML text extraction)
3. Send to Claude with prompt: analyse business, suggest additions to USPs, key messages, and persona keywords
4. Return suggestions as a structured diff (not auto-applied) — frontend shows accept/reject per suggestion

### Director Suggestions Agent Behaviour
When `GET /api/clients/{id}/suggestions` is called:
1. Fetch summaries from all three backends: `/api/campaigns/clients/{id}/summary`, `/api/ads/clients/{id}/summary`, `/api/webdev/clients/{id}/summary`
2. Build a state snapshot: what's running, what's completed, what's absent
3. Send to Claude with a prompt that evaluates the state against digital marketing best practices
4. Return ordered list of suggestion objects: `{id, priority, service, title, description, action_label, action_url}`

---

## Existing Backend Modifications

### What to change in all three existing backends

1. **Remove frontend directories** — the unified frontend replaces them
2. **Add brand DNA client** — a lightweight `httpx` async client that calls Brand DNA Service `/internal/clients/{id}/brand-context`. Cache result in memory for 5 minutes per `client_id`.
3. **Inject brand context in BaseAgent** — before calling Claude, fetch brand context and prepend the brand DNA block to the system prompt
4. **Add `client_id` (UUID) field** — standardise to UUID matching Brand DNA Service. Run an Alembic migration to add a `brand_dna_client_id` UUID column to the existing `clients` table.
5. **Add summary endpoint** — `GET /api/{service}/clients/{client_id}/summary` returns: `{client_id, active_count, completed_count, last_activity, status_summary}`
6. **Add `GET /internal/health`** — returns `{"service": "...", "status": "ok"}`

### Campaign Director specific
- The `BrandGuidelines` model currently lives here. Keep it for campaign-specific overrides, but treat Brand DNA Service as the source of truth. If Brand DNA exists, it takes precedence.

### Google Ads specific
- Brand DNA injected into: `CreatorAgent` (campaign naming and copy), `ReporterAgent` (narrative tone and language)
- APScheduler timezone stays SAST

### WebDev specific
- Brand DNA injected into: `ContentAgent` (page copy), `SEOAgent` (inject ICP persona `seo_keywords` directly into keyword lists), `MediaAgent` (inject `visual_style` and `primary_color` into image generation prompts)

---

## Frontend Build Spec

### Tech Stack
- React 18 + TypeScript + Vite
- TailwindCSS (utility-first styling)
- React Query (server state, per-service query keys)
- React Router v6 (nested routes)
- Zustand (minimal global state: active client, auth)

### Route Structure
```
/                           → redirect to /clients
/clients                    → ClientList
/clients/new                → CreateClient (→ brand DNA wizard)
/clients/:id                → ClientHub
/clients/:id/brand-dna      → BrandDNAView
/clients/:id/brand-dna/setup → BrandDNAWizard (multi-step)
/clients/:id/campaigns      → CampaignModule
/clients/:id/campaigns/:cid → CampaignDetail
/clients/:id/ads            → AdsModule
/clients/:id/ads/:aid       → AdsAccountDetail
/clients/:id/webdev         → WebdevModule
/clients/:id/webdev/:pid    → ProjectDetail
```

### Client Hub layout
```
┌─────────────────────────────────────────────────────┐
│  [← Clients]  Acme Corp                [Edit Brand] │
├──────────────────┬──────────────────────────────────┤
│  BRAND DNA       │  DIRECTOR SUGGESTIONS             │
│  snapshot card   │  ranked action cards              │
├────────┬─────────┴──────┬──────────────────────────-┤
│CAMPAIGNS│  GOOGLE ADS   │  WEBSITES                  │
│ status  │  status card  │  status card               │
│ card    │  [Open ↗]     │  [Open ↗]                 │
│ [Open ↗]│               │                            │
└────────┴───────────────-┴────────────────────────────┘
```

### Shared Components
- `<PipelineVisualiser />` — renders an agent task pipeline with status badges (used by Campaigns and WebDev)
- `<ApprovalGateCard />` — approve/reject with notes (used by Campaigns and WebDev)
- `<ApprovalQueueItem />` — approve/reject/execute (Google Ads pattern)
- `<BrandDNABadge />` — compact brand summary chip shown in headers
- `<SuggestionCard />` — Director suggestion with action button
- `<TokenCostBadge />` — shows token count + cost for a completed task
- `<WebSocketStatus />` — connection indicator for real-time updates

### API Clients (`src/api/`)
Each file exports typed async functions using `fetch` + React Query. Base URLs are environment variables:
```
VITE_BRAND_DNA_API=http://localhost:8000
VITE_CAMPAIGNS_API=http://localhost:8001
VITE_ADS_API=http://localhost:8002
VITE_WEBDEV_API=http://localhost:8003
```

---

## Build Order

Build in this exact order — each phase unblocks the next:

1. **Brand DNA Service** — foundation, must exist before modifying other backends
2. **Combined Frontend skeleton** — routing, layout, client list/create, brand DNA wizard (no service modules yet)
3. **Brand DNA injection in all 3 backends** — add brand context client + BaseAgent injection
4. **Frontend: Campaign Module** — port existing React UI into unified frontend module
5. **Frontend: Google Ads Module** — port existing vanilla JS views into React module
6. **Frontend: WebDev Module** — port existing React UI into unified frontend module
7. **Director Suggestions** — wire up cross-service suggestion engine
8. **Root docker-compose** — unified deployment

---

## Environment Variables (All Services)

### Brand DNA Service
```
DATABASE_URL=postgresql://...
ANTHROPIC_API_KEY=...
INTERNAL_API_SECRET=...          # shared secret for internal endpoints
PORT=8000
```

### Campaign Director (additions)
```
BRAND_DNA_SERVICE_URL=http://brand-dna:8000
INTERNAL_API_SECRET=...
```

### Google Ads (additions)
```
BRAND_DNA_SERVICE_URL=http://ads:8000
INTERNAL_API_SECRET=...
```

### WebDev (additions)
```
BRAND_DNA_SERVICE_URL=http://webdev:8000
INTERNAL_API_SECRET=...
```

---

## Key Principles for Claude Agents Across All Services

- Always use `claude-sonnet-4-6` as the default model
- Always enable prompt caching on the Brand DNA block and any long system prompts
- Always return structured JSON when the agent output needs to be parsed
- Always store `input_tokens`, `output_tokens`, `cost_usd` on every agent run record
- Keep system prompts in dedicated `.py` files as constants — not inline in agent logic
- Never hardcode client data in prompts — always fetch from Brand DNA Service
