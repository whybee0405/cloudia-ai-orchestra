# CloudIA AI Orchestra — Master Architecture

## Overview

A unified digital marketing AI platform for CloudIA's internal team. Three specialist agent workforces (Social Campaigns, Google Ads, Web Development) operate under a shared client-centric frontend, each referencing a centralised Brand DNA layer so every output is perfectly tailored to the client's identity.

---

## System Map

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLOUDIA AI FRONTEND                          │
│              Single React/TypeScript/Vite SPA                   │
│  Client Hub → Brand DNA → Campaigns | Google Ads | Web Dev      │
└──────────────────────┬──────────────────────────────────────────┘
                       │ HTTP
              ┌────────▼────────┐
              │   NGINX GATEWAY │  (routes by path prefix)
              └──┬──┬───┬───┬──┘
                 │  │   │   │
        ┌────────┘  │   │   └────────────┐
        │           │   │                │
┌───────▼──────┐ ┌──▼───▼───┐ ┌─────────▼──────┐ ┌──────────────┐
│  BRAND DNA   │ │ CAMPAIGN  │ │  GOOGLE ADS    │ │   WEBDEV     │
│   SERVICE    │ │ DIRECTOR  │ │    SERVICE     │ │   SERVICE    │
│  :8000       │ │  :8001    │ │    :8002       │ │   :8003      │
│              │ │           │ │                │ │              │
│ FastAPI      │ │ FastAPI   │ │ FastAPI        │ │ FastAPI      │
│ PostgreSQL   │ │ + Celery  │ │ + APScheduler  │ │ + Celery     │
│              │ │ + Redis   │ │                │ │ + Redis      │
└──────┬───────┘ └─────┬─────┘ └────────┬───────┘ └──────┬───────┘
       │               │                │                 │
       │         ┌─────▼──────────────────────────────────▼──────┐
       └─────────►         BRAND DNA READ API                     │
                 │  All agents fetch brand_dna on task start      │
                 └────────────────────────────────────────────────┘
```

---

## Services

### 1. Brand DNA Service (NEW) — `cloudia-ai-brand-dna-service/`

**Purpose:** Source of truth for client identity. All other services call this to get brand context before generating any output.

**Responsibilities:**
- Client CRUD (canonical client record, shared client_id across all services)
- Brand DNA onboarding form + agent enrichment
- ICP Persona wizard
- Master Digital Marketing Director Agent (cross-service suggestion engine)
- Brand DNA read API consumed internally by all other backends

**Tech Stack:** Python 3.12 / FastAPI / PostgreSQL / SQLAlchemy / Alembic / Anthropic Claude

**Database Models:**

```
Client
├── id (UUID, shared across all services)
├── name, website_url, industry, sub_industry
├── location, timezone, founded_year
└── created_at, updated_at

BrandDNA
├── client_id (FK → Client)
├── tagline
├── brand_voice: tone (formal/casual/playful/authoritative)
├── language_style (text)
├── personality_traits (JSON array)
├── primary_color, secondary_colors (JSON), accent_color
├── heading_font, body_font
├── logo_url
├── visual_style (minimalist/bold/editorial/dark-tech/etc.)
├── usps (JSON array)
├── pain_points_addressed (JSON array)
├── key_messages (JSON array)
├── competitors (JSON array)
├── differentiators (JSON array)
└── enriched_at (when agent last enriched it)

ICPPersona
├── client_id (FK → Client)
├── persona_name (e.g. "Sarah the SME Owner")
├── age_min, age_max
├── gender_skew
├── income_bracket
├── location_type (urban/suburban/rural)
├── interests (JSON array)
├── values (JSON array)
├── pain_points (JSON array)
├── goals (JSON array)
├── preferred_channels (JSON array)
├── seo_keywords (JSON array)          ← used by WebDev + Campaigns SEO agents
├── vocabulary (JSON array)            ← tone/language cues for copy agents
└── order (display order, 1-5 max)
```

**API Endpoints:**
```
GET    /api/clients                         List all clients
POST   /api/clients                         Create client
GET    /api/clients/{id}                    Get client
PATCH  /api/clients/{id}                    Update client

GET    /api/clients/{id}/brand-dna          Get brand DNA
PUT    /api/clients/{id}/brand-dna          Save brand DNA form
POST   /api/clients/{id}/brand-dna/enrich   Trigger agent enrichment

GET    /api/clients/{id}/personas           List ICP personas
POST   /api/clients/{id}/personas           Create persona
PATCH  /api/clients/{id}/personas/{pid}     Update persona
DELETE /api/clients/{id}/personas/{pid}     Remove persona
GET    /api/clients/{id}/personas/templates Get industry persona templates

GET    /api/clients/{id}/suggestions        Cross-service suggestions (Director Agent)

# Internal read endpoint — called by other backends
GET    /internal/clients/{id}/brand-context  Returns brand_dna + personas (compact)
```

**Brand DNA Enrichment Agent:**
When user saves the form, optionally triggers a Claude agent that:
- Analyzes the website URL (if provided) to extract visual and copy style
- Suggests additional USPs based on industry
- Recommends persona keywords from industry data
- Returns enrichment suggestions the user can accept/reject

**Master Digital Marketing Director Agent:**
Called via `GET /api/clients/{id}/suggestions`. Fetches live state from all 3 backends, then uses Claude to generate a prioritised suggestion list:
- "Your Google Ads CTR dropped 22% this week — consider refreshing ad creative via Campaign Director"
- "WebDev project is complete — ready to launch a social media campaign?"
- "No Google Ads account linked yet — would you like to set one up?"

---

### 2. Campaign Director Service (EXISTING — modified)
**Port:** 8001 | **Path prefix:** `/api/campaigns`

**Changes required:**
- Remove standalone frontend (replaced by unified frontend)
- Add `GET /internal/health` endpoint
- Inject brand DNA at agent start: all agents call Brand DNA Service `/internal/clients/{id}/brand-context` before building their Claude prompt
- Add `GET /api/campaigns/clients/{client_id}/summary` — compact state for Director suggestions
- Standardise client_id to match Brand DNA Service UUID

**Brand DNA injection pattern (all agents):**
```python
# In BaseAgent.run()
brand_context = await brand_dna_client.get_context(self.client_id)
# Injected into every Claude system prompt as structured block
```

---

### 3. Google Ads Service (EXISTING — modified)
**Port:** 8002 | **Path prefix:** `/api/ads`

**Changes required:**
- Remove standalone vanilla JS frontend
- Add `GET /internal/health` endpoint
- Inject brand DNA into: `CreatorAgent` (campaign copy), `ReporterAgent` (narrative tone)
- Add `GET /api/ads/clients/{client_id}/summary` — for Director suggestions
- Standardise client_id to Brand DNA Service UUID

---

### 4. WebDev Service (EXISTING — modified)
**Port:** 8003 | **Path prefix:** `/api/webdev`

**Changes required:**
- Remove standalone frontend
- Add `GET /internal/health` endpoint
- Inject brand DNA into: `ContentAgent` (copy tone), `SEOAgent` (ICP keywords), `MediaAgent` (visual style)
- Add `GET /api/webdev/clients/{client_id}/summary` — for Director suggestions
- Standardise client_id to Brand DNA Service UUID

---

### 5. Combined Frontend (NEW) — `cloudia-ai-frontend/`
**Tech Stack:** React 18 / TypeScript / Vite / TailwindCSS / React Query / React Router v6 / Zustand

**Module Structure:**
```
src/
├── app/
│   ├── router.tsx              Top-level routes
│   ├── layout/                 Shell (sidebar, header)
│   └── providers.tsx           QueryClient, Auth, global state
├── modules/
│   ├── clients/                Client list + create
│   ├── brand-dna/
│   │   ├── wizard/             Multi-step onboarding form
│   │   ├── persona-wizard/     ICP persona builder + templates
│   │   └── brand-dna-view/     Read/edit existing brand DNA
│   ├── campaigns/              Campaign Director module
│   ├── google-ads/             Google Ads module
│   ├── webdev/                 WebDev module
│   └── suggestions/            Cross-agent suggestion cards
├── shared/
│   ├── components/             Buttons, Cards, Badges, Modals, Pipeline visualiser
│   ├── hooks/                  useClient, useBrandDNA, useWebSocket
│   └── types/                  Shared TypeScript interfaces
└── api/
    ├── brand-dna.ts            Brand DNA Service client
    ├── campaigns.ts            Campaign Director client
    ├── google-ads.ts           Google Ads client
    └── webdev.ts               WebDev client
```

**Primary UX Flow (client-centric):**
```
/clients                        — Client list
/clients/new                    — Create client
/clients/:id                    — Client Hub (dashboard)
  └─ /clients/:id/brand-dna     — Brand DNA view/edit
  └─ /clients/:id/brand-dna/setup  — Onboarding wizard (new clients)
  └─ /clients/:id/campaigns     — Campaign Director module
  └─ /clients/:id/ads           — Google Ads module
  └─ /clients/:id/webdev        — WebDev module
```

**Client Hub (`/clients/:id`):**
- Brand DNA summary card (voice, colours, top personas)
- Active work cards: running campaigns / active ad accounts / live projects
- Director Suggestions panel (from Brand DNA Service)
- Quick-launch buttons: "New Campaign", "New Website", "Manage Ads"

**Brand DNA Wizard (new client flow):**
```
Step 1: Business Basics       (name, URL, industry, location)
Step 2: Brand Voice           (tone selector, personality traits)
Step 3: Visual Identity       (colour pickers, font selector, visual style)
Step 4: Key Messages          (USPs, pain points, differentiators)
Step 5: ICP Personas          (persona builder with industry templates)
Step 6: Review + Enrich       (agent enrichment suggestions, confirm)
```

**ICP Persona Wizard:**
- Industry-specific template gallery (e.g. "SME Owner", "Decision Maker", "End Consumer")
- Demographic sliders + toggles
- Keyword suggestions (surfaced from Claude, editable)
- Preview: how this persona shapes copy tone and SEO keywords

---

## nginx API Gateway

```nginx
# /etc/nginx/sites-available/cloudia-orchestra
server {
    listen 80;

    location /api/brand/     { proxy_pass http://localhost:8000; }
    location /api/campaigns/ { proxy_pass http://localhost:8001; }
    location /api/ads/       { proxy_pass http://localhost:8002; }
    location /api/webdev/    { proxy_pass http://localhost:8003; }
    location /               { proxy_pass http://localhost:3000; }  # React dev / built static
}
```

---

## Brand DNA Injection (All Backends)

Every Claude prompt across all three backends will include a structured brand context block:

```
=== BRAND DNA: {client_name} ===
Industry: {industry}
Brand Voice: {tone} — {language_style}
Personality: {personality_traits}
Visual Style: {visual_style} | Primary Colour: {primary_color}
USPs: {usps}
Key Messages: {key_messages}

TARGET PERSONAS:
1. {persona_name} | Age: {age_min}-{age_max}
   Pain Points: {pain_points}
   Goals: {goals}
   SEO Keywords: {seo_keywords}
   Vocabulary: {vocabulary}
===============================
```

This block is injected at the start of the system prompt for every agent call, cached per client per session (5-minute TTL matching Claude's prompt cache window).

---

## Cross-Service Suggestion Logic

The Master Director Agent checks:

| Condition | Suggestion |
|-----------|------------|
| WebDev project completed, no active campaign | "Launch a social campaign for the new site" |
| Google Ads CTR < baseline by >20% | "Refresh ad creative via Campaign Director" |
| Campaign running, no Google Ads | "Amplify reach with Google Ads" |
| No website project | "Build a website first to anchor your digital presence" |
| Brand DNA incomplete | "Complete Brand DNA to unlock tailored outputs" |
| Personas missing | "Add ICP personas to improve SEO and copy targeting" |

Suggestions are ranked by impact and shown as actionable cards in the Client Hub.

---

## Shared Conventions (All Services)

- `client_id`: UUID, Brand DNA Service is the canonical source
- All agents log tokens + cost to their local `agent_tasks` / `agent_runs` table
- All backends expose `GET /internal/health` and `GET /internal/clients/{id}/summary`
- Fernet encryption for all OAuth + platform credentials
- Structured logging via `structlog`
- Alembic for all DB migrations
- `.env` excluded from git; `.env.example` committed

---

## Deployment (Docker Compose — Monorepo Root)

```yaml
# docker-compose.yml (root)
services:
  frontend:         build: ./cloudia-ai-frontend
  brand-dna:        build: ./cloudia-ai-brand-dna-service
  campaigns-api:    build: ./cloudia-ai-campaign-director-agent/backend
  campaigns-worker: build: ./cloudia-ai-campaign-director-agent/backend (celery)
  ads:              build: ./cloudia-ai-googleads-agent
  webdev-api:       build: ./cloudia-ai-webdev-agent/backend
  webdev-worker:    build: ./cloudia-ai-webdev-agent/backend (celery)
  nginx:            image: nginx
  postgres-brand:   image: postgres:15   # Brand DNA DB
  postgres-campaigns: image: postgres:15
  postgres-ads:     image: postgres:15
  postgres-webdev:  image: postgres:15
  redis:            image: redis:7        # Shared by Campaigns + WebDev workers
```

Each backend keeps its own DB. `client_id` (UUID from Brand DNA Service) is the shared foreign key that links everything together.
