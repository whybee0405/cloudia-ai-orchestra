# CloudIA Website Agent System — Master Project Prompt
# For use with: Claude Code / Codex / GitHub Copilot (Sonnet)
# Version: 1.0 | Owner: CloudIA
# Companion system to: google_ads_agents (separate repo)

---

## HOW TO USE THIS FILE

Paste MASTER_PROMPT.md + PROGRESS.md at the start of every coding session.
The model reads both, picks up from where the last session ended.
At session end: model updates PROGRESS.md before closing.
Never re-architect. Never rename. Follow the spec. Document deviations in PROGRESS.md.

---

## 1. PROJECT BRIEF

**Company:** CloudIA — South African digital agency serving SMEs.

**What we are building:**
A multi-agent AI system that builds, populates, and deploys professional websites
for SME clients on WordPress and Shopify. Operated internally by CloudIA — not
a client-facing SaaS. Agents do the heavy lifting; humans approve before anything
goes live.

**Core principles:**
- Director Agent orchestrates. Subagents execute. Humans approve at gates.
- All content is client-specific — no generic filler copy.
- Platform choice (WordPress vs Shopify) is determined by the client brief.
- Docker on both dev and prod. No snowflake servers.
- GUI is lightweight and operator-focused — not a marketing page.
- System must run comfortably on a R500/month VPS.

---

## 2. TECH STACK (exact — do not substitute)

### Backend
| Tool | Version | Purpose |
|---|---|---|
| Python | 3.11+ | All agents and API |
| FastAPI | 0.111 | REST API + WebSocket for live status |
| SQLAlchemy | 2.0 | ORM |
| Alembic | 1.13 | Migrations |
| Celery | 5.3 | Async agent task queue |
| Redis | 7 | Celery broker + result backend |
| PostgreSQL | 15 | Primary database |
| anthropic | 0.26.0 | Claude Sonnet for all AI reasoning |
| wordpress-api | 2.1 | WordPress REST API client |
| ShopifyAPI | 12.4 | Shopify Admin API client |
| httpx | 0.27 | Async HTTP for direct API calls |
| python-dotenv | 1.0 | Env management |
| Pillow | 10.3 | Image processing |
| pytest | 8.2 | Testing |
| ruff | 0.4 | Linting |

### Frontend
| Tool | Version | Purpose |
|---|---|---|
| React | 18 | UI framework |
| Vite | 5 | Build tool |
| Tailwind CSS | 3 | Styling — utility only, no component libs |
| React Query | 5 | Server state management |
| React Router | 6 | Client routing |
| Axios | 1.7 | API calls |
| Lucide React | 0.383 | Icons only |

### Infrastructure
| Tool | Purpose |
|---|---|
| Docker | Containerisation |
| Docker Compose | Dev and prod orchestration |
| Nginx | Reverse proxy (prod) |
| Certbot | SSL (prod) |

---

## 3. FOLDER STRUCTURE (build exactly this)

```
cloudia-website-agents/
│
├── docker/
│   ├── Dockerfile.api              # FastAPI + Celery worker image
│   ├── Dockerfile.frontend         # React build image
│   ├── nginx/
│   │   └── nginx.conf              # Prod reverse proxy config
│   ├── docker-compose.yml          # Dev — hot reload, exposed ports
│   └── docker-compose.prod.yml     # Prod — built images, nginx, no raw ports
│
├── backend/
│   ├── main.py                     # FastAPI app entry point
│   ├── config.py                   # All settings from env vars
│   ├── worker.py                   # Celery worker entry point
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseAgent — logging, error handling, token tracking
│   │   ├── director.py             # Director — routes brief, orchestrates pipeline
│   │   │
│   │   ├── shared/                 # Used by both WordPress and Shopify pipelines
│   │   │   ├── __init__.py
│   │   │   ├── content_agent.py    # Generates all copy via Claude
│   │   │   ├── media_agent.py      # Sources + optimises images (Unsplash/Pexels)
│   │   │   └── seo_agent.py        # Meta tags, schema markup, sitemap
│   │   │
│   │   ├── wordpress/
│   │   │   ├── __init__.py
│   │   │   ├── structure_agent.py  # Decides page architecture + nav
│   │   │   ├── builder_agent.py    # Creates site via WP REST API + WP-CLI
│   │   │   └── qa_agent.py         # Validates built site
│   │   │
│   │   └── shopify/
│   │       ├── __init__.py
│   │       ├── structure_agent.py  # Decides collections + page architecture
│   │       ├── builder_agent.py    # Creates store via Shopify Admin API
│   │       ├── theme_agent.py      # Applies brand colours + fonts to theme
│   │       └── qa_agent.py         # Validates built store
│   │
│   ├── platforms/
│   │   ├── wordpress/
│   │   │   ├── __init__.py
│   │   │   ├── client.py           # WP REST API wrapper
│   │   │   ├── wpcli.py            # WP-CLI commands via SSH/subprocess
│   │   │   └── templates.py        # Page/post payload builders
│   │   └── shopify/
│   │       ├── __init__.py
│   │       ├── client.py           # Shopify Admin API wrapper
│   │       └── templates.py        # Product/page payload builders
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── claude.py               # Anthropic API wrapper
│   │   ├── context_builder.py      # Injects client brief into every prompt
│   │   └── prompts/
│   │       ├── __init__.py
│   │       ├── director.py
│   │       ├── content.py
│   │       ├── media.py
│   │       ├── seo.py
│   │       ├── wp_structure.py
│   │       ├── wp_builder.py
│   │       ├── wp_qa.py
│   │       ├── shopify_structure.py
│   │       ├── shopify_builder.py
│   │       ├── shopify_theme.py
│   │       └── shopify_qa.py
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py               # All SQLAlchemy models
│   │   ├── session.py              # Session factory
│   │   └── migrations/             # Alembic files
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── app.py                  # FastAPI app + CORS + middleware
│   │   ├── websocket.py            # Live agent status updates to GUI
│   │   ├── schemas.py              # Pydantic models
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── projects.py         # Project CRUD + trigger pipeline
│   │       ├── approvals.py        # Approval gate management
│   │       ├── content.py          # Review/edit generated content
│   │       └── settings.py         # Platform credentials management
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── celery_app.py           # Celery configuration
│   │   └── pipeline_tasks.py       # Celery tasks wrapping each agent
│   │
│   └── notifications/
│       ├── __init__.py
│       └── email.py
│
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── api/
│   │   │   ├── client.js           # Axios instance
│   │   │   ├── projects.js
│   │   │   ├── approvals.js
│   │   │   └── content.js
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx       # All projects, status overview
│   │   │   ├── NewProject.jsx      # Client brief intake form
│   │   │   ├── ProjectDetail.jsx   # Pipeline status per project
│   │   │   ├── ContentReview.jsx   # Review/edit generated content
│   │   │   ├── ApprovalQueue.jsx   # All pending approvals
│   │   │   └── Settings.jsx        # Platform credentials
│   │   ├── components/
│   │   │   ├── PipelineStatus.jsx  # Visual agent pipeline tracker
│   │   │   ├── AgentTaskCard.jsx   # Individual task status card
│   │   │   ├── ApprovalCard.jsx    # Approve/reject/revise gate card
│   │   │   ├── ContentEditor.jsx   # Inline content editing
│   │   │   ├── BriefForm.jsx       # Multi-step brief intake
│   │   │   └── StatusBadge.jsx     # Reusable status pill
│   │   └── hooks/
│   │       ├── useProjectStatus.js # WebSocket hook for live updates
│   │       └── useApprovals.js
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
│
├── tests/
│   ├── conftest.py
│   ├── factories.py
│   ├── mocks/
│   │   ├── mock_claude.py
│   │   ├── mock_wordpress.py
│   │   └── mock_shopify.py
│   ├── test_director.py
│   ├── test_content_agent.py
│   ├── test_wp_builder.py
│   ├── test_shopify_builder.py
│   ├── test_seo_agent.py
│   ├── test_approval_gates.py
│   ├── test_context_builder.py
│   └── test_api.py
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── AGENT_SPECS.md
│   ├── DATABASE.md
│   ├── DOCKER.md
│   ├── ONBOARDING_CLIENT.md
│   └── DECISIONS.md
│
├── MASTER_PROMPT.md                # This file — never changes
├── PROGRESS.md                     # Session handoff — updated every session
├── STRESS_TEST_PROMPT.md
├── .env.example
├── .gitignore
└── README.md
```

---

## 4. AGENT ARCHITECTURE

### Director Agent (agents/director.py)
**Trigger:** New project created via GUI
**Role:** Analyzes client brief, selects platform, builds task pipeline, hands to Celery

```
Inputs:
  - client_id
  - raw brief (from GUI form)

Steps:
  1. Load client profile from DB
  2. Analyze brief with Claude:
     - Does client sell products? → Shopify
     - Service/professional/restaurant? → WordPress
     - Ambiguous? → flag for human platform selection
  3. Generate project plan:
     { platform, pipeline_steps, estimated_pages, content_requirements }
  4. Write project to DB (status: planned)
  5. Write all AgentTask rows for this project (status: pending)
  6. Create ApprovalGate rows at correct pipeline positions
  7. Trigger first Celery task: content_agent

Outputs:
  - project_id
  - pipeline plan written to DB
  - first task queued
```

### Content Agent — Shared (agents/shared/content_agent.py)
**Trigger:** Director queues it as first task
**Role:** Generates ALL copy for the entire site before any building starts

```
Inputs:
  - project_id
  - platform (wordpress | shopify)
  - page_list from director plan

Steps:
  1. Load full client context via context_builder
  2. For each required page/section:
     Claude generates:
       - Page title
       - H1 heading
       - Body copy (paragraphs, bullets where appropriate)
       - CTA text
       - Meta title (under 60 chars)
       - Meta description (under 160 chars)
  3. For Shopify: also generates product descriptions per product
  4. Stores each piece to generated_content table (status: draft)
  5. Writes ApprovalGate: 'content_review' (status: pending)
  6. Notifies operator via email + WebSocket

IMPORTANT: Does NOT proceed to next agent until content_review gate is approved.
Human reads, edits, approves content before a single API call to WP or Shopify.
```

### Media Agent — Shared (agents/shared/media_agent.py)
**Trigger:** content_review gate approved
**Role:** Sources relevant images from Unsplash/Pexels API

```
Steps:
  1. Read approved content to understand topics per page
  2. Generate search queries per page/section
  3. Call Unsplash API (free tier: 50 req/hour)
  4. Download + resize images to web-optimised dimensions
  5. Store image metadata to project_media table
  6. No approval gate — operator can swap images in ContentReview page
```

### SEO Agent — Shared (agents/shared/seo_agent.py)
**Trigger:** Builder agent completes
**Role:** Adds technical SEO layer after site is built

```
Steps:
  1. Validate all meta titles are under 60 chars
  2. Validate all meta descriptions are under 160 chars
  3. Generate schema markup (LocalBusiness, Product, etc.) per page type
  4. Generate XML sitemap
  5. Push schema to built site via platform API
  6. Submit sitemap to platform
  7. Log SEO score per page to agent_tasks output
```

---

### WordPress Pipeline

#### WP Structure Agent (agents/wordpress/structure_agent.py)
**Trigger:** content_review approved
**Role:** Designs page hierarchy and navigation

```
Claude decides:
  - Which pages to create (Home, About, Services, Contact, Blog?)
  - Page hierarchy (parent/child relationships)
  - Navigation menu structure (primary, footer)
  - Which page uses which template (full-width, sidebar, landing)
  - Whether WooCommerce is needed

Output: structure_plan JSON stored to project
```

#### WP Builder Agent (agents/wordpress/builder_agent.py)
**Trigger:** structure_agent completes
**Role:** Creates the actual WordPress site

```
Pre-requisites:
  - WordPress install must already exist (client provisions their own hosting)
  - Operator enters: site_url, admin_user, app_password in Settings
  - WP REST API app passwords used for auth (not username/password)

Steps:
  1. Verify WP REST API is accessible
  2. Create pages via REST API with approved content
  3. Set page templates per structure plan
  4. Create navigation menus via REST API
  5. Upload media via REST API media endpoint
  6. Set featured images per page
  7. Configure site title, tagline, timezone via WP Options API
  8. If WooCommerce needed: create products via WC REST API
  9. Set homepage as static page

WP-CLI (optional, via SSH if server access available):
  - Install + activate theme
  - Install + activate required plugins
  - Update permalink structure
  - Clear cache

Output: site_url written to project, status → awaiting_approval
Creates ApprovalGate: 'site_review'
```

#### WP QA Agent (agents/wordpress/qa_agent.py)
**Trigger:** builder completes
**Role:** Validates the built site before human sees it

```
Checks:
  - All pages return HTTP 200
  - No pages have empty content
  - Featured images set on all pages
  - Meta titles present on all pages
  - Navigation menu exists and has correct items
  - Homepage is set as front page (not blog)
  - Contact page has form or contact details
  - All internal links resolve (no 404s)
  - Site loads under 3 seconds (basic check via httpx timing)

Output: qa_report JSON stored to agent_tasks
If any CRITICAL check fails: block site_review gate, notify operator
If only warnings: pass gate with warnings noted
```

---

### Shopify Pipeline

#### Shopify Structure Agent (agents/shopify/structure_agent.py)
**Trigger:** content_review approved
**Role:** Designs store architecture

```
Claude decides:
  - Collection structure (how products are grouped)
  - Navigation (main menu, footer menu)
  - Which pages to create (About, Contact, FAQ, Shipping Policy)
  - Product variant structure (size, colour, etc.)
  - Whether blog is needed

Output: structure_plan JSON stored to project
```

#### Shopify Builder Agent (agents/shopify/builder_agent.py)
**Trigger:** structure_agent completes
**Role:** Builds the store via Shopify Admin API

```
Pre-requisites:
  - Client must have created their Shopify store
  - Operator enters: shop_url, access_token in Settings

Steps:
  1. Create Collections
  2. Create Products with variants, prices, descriptions
  3. Upload product images
  4. Create Pages (About, Contact, FAQ, etc.) with approved content
  5. Create Navigation menus
  6. Set store metadata (title, description, currency)
  7. Configure checkout settings

Output: store_url written to project, status → awaiting_approval
Creates ApprovalGate: 'store_review'
```

#### Shopify Theme Agent (agents/shopify/theme_agent.py)
**Trigger:** builder_agent completes
**Role:** Applies brand identity to the active theme

```
Steps:
  1. Read brand_colours and brand_fonts from client profile
  2. Fetch active theme settings_data.json via Assets API
  3. Inject brand colours into theme colour scheme settings
  4. Inject font preferences if theme supports it
  5. Upload logo image via Assets API
  6. Push updated settings_data.json back to theme

Note: Does not modify theme code — only theme settings.
Theme code modifications require manual work by operator.
```

#### Shopify QA Agent (agents/shopify/qa_agent.py)
**Trigger:** theme_agent completes
**Role:** Validates built store

```
Checks:
  - All collections have at least one product
  - All products have images, descriptions, prices
  - All pages return HTTP 200
  - Navigation menus exist
  - Store currency set correctly (ZAR by default)
  - Checkout accessible
  - Meta titles present on all pages
  - No products with R0 price (flag as critical)

Output: qa_report JSON, same gate logic as WP QA
```

---

## 5. DATABASE SCHEMA (db/models.py)

### clients
```sql
id                  SERIAL PRIMARY KEY
name                VARCHAR(255) NOT NULL
industry            VARCHAR(100)
business_type       VARCHAR(50)         -- 'ecommerce' | 'service' | 'restaurant' | etc
target_audience     TEXT
usp                 TEXT                -- unique selling proposition
tone_of_voice       VARCHAR(50)         -- 'professional' | 'friendly' | 'luxury' | 'bold'
brand_colours       JSONB               -- { primary: '#FF0000', secondary: '#000', accent: '#FFF' }
brand_fonts         JSONB               -- { heading: 'Playfair Display', body: 'Inter' }
logo_url            TEXT
contact_email       VARCHAR(255)
contact_phone       VARCHAR(50)
address             TEXT
city                VARCHAR(100)
country             VARCHAR(100) DEFAULT 'South Africa'
website_url         TEXT                -- existing site if any
social_links        JSONB
created_at          TIMESTAMP DEFAULT NOW()
notes               TEXT
```

### projects
```sql
id                  SERIAL PRIMARY KEY
client_id           INTEGER REFERENCES clients(id)
platform            VARCHAR(20) NOT NULL    -- 'wordpress' | 'shopify'
status              VARCHAR(30) DEFAULT 'planned'
                    -- planned | running | awaiting_content_review
                    -- awaiting_site_review | completed | failed | cancelled
brief               JSONB NOT NULL          -- full raw brief from GUI form
pipeline_plan       JSONB                   -- director's output plan
site_url            TEXT                    -- live URL once built
admin_url           TEXT
credentials         JSONB                   -- encrypted: app passwords, tokens
estimated_pages     INTEGER
actual_pages        INTEGER
created_at          TIMESTAMP DEFAULT NOW()
completed_at        TIMESTAMP
operator_notes      TEXT
```

### agent_tasks
```sql
id                  SERIAL PRIMARY KEY
project_id          INTEGER REFERENCES projects(id)
agent_name          VARCHAR(100) NOT NULL
pipeline_order      INTEGER                 -- 1, 2, 3... execution order
status              VARCHAR(20) DEFAULT 'pending'
                    -- pending | running | completed | failed | skipped | blocked
input_data          JSONB
output_data         JSONB
tokens_used         INTEGER
cost_usd            NUMERIC(8,6)
started_at          TIMESTAMP
completed_at        TIMESTAMP
error               TEXT
retry_count         INTEGER DEFAULT 0
celery_task_id      VARCHAR(255)
```

### approval_gates
```sql
id                  SERIAL PRIMARY KEY
project_id          INTEGER REFERENCES projects(id)
gate_name           VARCHAR(100)
                    -- 'content_review' | 'site_review' | 'store_review'
pipeline_order      INTEGER
status              VARCHAR(20) DEFAULT 'pending'
                    -- pending | approved | rejected | revision_requested
notes               TEXT                    -- operator feedback on rejection
created_at          TIMESTAMP DEFAULT NOW()
reviewed_at         TIMESTAMP
reviewed_by         VARCHAR(100)
```

### generated_content
```sql
id                  SERIAL PRIMARY KEY
project_id          INTEGER REFERENCES projects(id)
page_slug           VARCHAR(255)            -- 'home' | 'about' | 'services' | 'contact'
content_type        VARCHAR(50)             -- 'page' | 'product' | 'post' | 'collection'
title               VARCHAR(255)
h1                  VARCHAR(255)
body_content        TEXT
cta_text            VARCHAR(100)
meta_title          VARCHAR(60)
meta_description    VARCHAR(160)
schema_markup       JSONB
status              VARCHAR(20) DEFAULT 'draft'
                    -- draft | approved | revision_requested | published
revision_notes      TEXT
platform_id         VARCHAR(100)            -- WP post ID or Shopify resource ID once published
```

### project_media
```sql
id                  SERIAL PRIMARY KEY
project_id          INTEGER REFERENCES projects(id)
page_slug           VARCHAR(255)
image_purpose       VARCHAR(100)            -- 'hero' | 'featured' | 'product' | 'gallery'
source              VARCHAR(50)             -- 'unsplash' | 'pexels' | 'client_upload'
source_id           VARCHAR(255)
source_url          TEXT
local_path          TEXT
optimised_path      TEXT
alt_text            TEXT
attribution         TEXT                    -- photographer credit
platform_media_id   VARCHAR(100)            -- ID once uploaded to WP/Shopify
```

### platform_credentials
```sql
id                  SERIAL PRIMARY KEY
client_id           INTEGER REFERENCES clients(id)
platform            VARCHAR(20)
site_url            TEXT
api_url             TEXT
access_token        TEXT                    -- store encrypted
app_password        TEXT                    -- WP app password, encrypted
shop_name           VARCHAR(255)
api_version         VARCHAR(20)
is_active           BOOLEAN DEFAULT TRUE
created_at          TIMESTAMP DEFAULT NOW()
last_verified_at    TIMESTAMP
```

---

## 6. DOCKER CONFIGURATION

### docker/docker-compose.yml (DEV)
```yaml
version: '3.9'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: cloudia_websites
      POSTGRES_USER: cloudia
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    command: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend:/app/backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://cloudia:${DB_PASSWORD}@db:5432/cloudia_websites
      - REDIS_URL=redis://redis:6379/0
    env_file: .env
    depends_on:
      - db
      - redis

  worker:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    command: celery -A backend.tasks.celery_app worker --loglevel=info --concurrency=4
    volumes:
      - ./backend:/app/backend
    environment:
      - DATABASE_URL=postgresql://cloudia:${DB_PASSWORD}@db:5432/cloudia_websites
      - REDIS_URL=redis://redis:6379/0
    env_file: .env
    depends_on:
      - db
      - redis

  frontend:
    build:
      context: ./frontend
      dockerfile: ../docker/Dockerfile.frontend
    command: npm run dev -- --host
    volumes:
      - ./frontend/src:/app/src
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://localhost:8000

volumes:
  postgres_data:
```

### docker/docker-compose.prod.yml (PROD)
```yaml
version: '3.9'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: cloudia_websites
      POSTGRES_USER: cloudia
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    command: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2
    env_file: .env.prod
    environment:
      - DATABASE_URL=postgresql://cloudia:${DB_PASSWORD}@db:5432/cloudia_websites
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped

  worker:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    command: celery -A backend.tasks.celery_app worker --loglevel=warning --concurrency=4
    env_file: .env.prod
    environment:
      - DATABASE_URL=postgresql://cloudia:${DB_PASSWORD}@db:5432/cloudia_websites
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: ../docker/Dockerfile.frontend
      target: production
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - certbot_certs:/etc/letsencrypt:ro
    depends_on:
      - api
      - frontend
    restart: unless-stopped

  certbot:
    image: certbot/certbot
    volumes:
      - certbot_certs:/etc/letsencrypt
      - certbot_www:/var/www/certbot

volumes:
  postgres_data:
  certbot_certs:
  certbot_www:
```

### docker/Dockerfile.api
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY alembic.ini .

EXPOSE 8000
```

### docker/Dockerfile.frontend
```dockerfile
FROM node:20-alpine AS development
WORKDIR /app
COPY package*.json .
RUN npm install
COPY . .
EXPOSE 5173

FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx-frontend.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

---

## 7. GUI SPECIFICATION (frontend/)

Simple operator dashboard. Dark theme. Functional over decorative.
No animations beyond subtle transitions. Data-dense but clean.

### Pages

#### Dashboard (/)
- Project summary cards: client name, platform badge, status, created date
- Status filter tabs: All / Running / Awaiting Review / Completed
- Quick stats bar: active projects, pending approvals, sites built this month
- "New Project" button → /new

#### New Project (/new)
Multi-step form — one screen per section:
```
Step 1: Select or create client
Step 2: Platform (WordPress / Shopify / Auto-detect)
Step 3: Business brief
  - What does the business do? (textarea)
  - Who is the target customer? (textarea)
  - What makes them different? (textarea — USP)
  - What action should visitors take? (CTA goal)
Step 4: Pages needed (checklist with custom add)
Step 5: Brand (colour pickers, font selectors, logo upload)
Step 6: Platform credentials (site URL, API key/app password)
Step 7: Review + Launch
```

#### Project Detail (/projects/:id)
- Pipeline visualiser: horizontal stepper showing each agent task
  Each step shows: agent name, status badge, started_at, completed_at, token cost
- Live WebSocket updates — steps turn green as they complete
- Approval gate cards: inline approve/reject/request revision
- Content preview: scrollable preview of generated content
- QA report: checklist of passes/failures from QA agent
- Action bar: Pause / Retry Failed Task / Cancel Project

#### Content Review (/projects/:id/content)
- One card per page/product
- Editable fields inline: title, h1, body, CTA, meta title, meta description
- Character counter on meta fields
- Approve individual pieces or bulk approve all
- "Regenerate" button per card — re-runs content agent for that page only

#### Approval Queue (/approvals)
- Aggregated view across all projects
- Grouped by gate type: Content Reviews / Site Reviews
- Each item shows: client name, project id, gate name, waiting since
- Quick approve/reject without leaving the queue

#### Settings (/settings)
- Platform credentials manager (add/edit/test connection)
- SMTP config for notifications
- Unsplash/Pexels API keys
- Anthropic API key display (masked)
- System status: DB connection, Redis, Celery worker heartbeat

### WebSocket (api/websocket.py)
Frontend connects to `ws://api/ws/projects/{project_id}`
Backend pushes events:
```json
{ "event": "task_started", "agent": "content_agent", "task_id": 3 }
{ "event": "task_completed", "agent": "content_agent", "task_id": 3, "cost_usd": 0.0034 }
{ "event": "gate_created", "gate": "content_review", "gate_id": 1 }
{ "event": "task_failed", "agent": "wp_builder", "error": "REST API auth failed" }
```

---

## 8. CONTEXT BUILDER (ai/context_builder.py)

Every Claude call receives this context. Never call Claude without it.

```python
def build_project_context(client: Client, project: Project) -> str:
    return f"""
=== CLIENT BRIEF ===
Business name: {client.name}
Industry: {client.industry}
Business type: {client.business_type}
Location: {client.city}, {client.country}
Target audience: {client.target_audience}
Unique selling proposition: {client.usp}
Tone of voice: {client.tone_of_voice}
Brand colours: {json.dumps(client.brand_colours)}
Existing website: {client.website_url or 'None'}
Contact: {client.contact_email} | {client.contact_phone}

=== PROJECT BRIEF ===
Platform: {project.platform}
{json.dumps(project.brief, indent=2)}

=== YOUR ROLE ===
You are a senior web copywriter and digital strategist working for CloudIA,
a South African digital agency. You are building a professional website for
this specific client. All content must:
1. Reflect the client's tone of voice exactly
2. Speak directly to their stated target audience
3. Be written for a South African market unless brief says otherwise
4. Never use generic filler copy — every sentence earns its place
5. Be factually grounded in the brief — do not invent services, products, or claims
6. Where asked for JSON output: return ONLY valid JSON, no markdown, no preamble
"""
```

---

## 9. ENVIRONMENT VARIABLES (.env.example)

```env
# Database
DB_PASSWORD=
DATABASE_URL=postgresql://cloudia:password@db:5432/cloudia_websites

# Redis
REDIS_URL=redis://redis:6379/0

# Anthropic
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Media APIs
UNSPLASH_ACCESS_KEY=
PEXELS_API_KEY=

# Email
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
NOTIFICATION_FROM=

# App
SECRET_KEY=                     # FastAPI session secret
ENVIRONMENT=development         # development | production
ALLOWED_ORIGINS=http://localhost:5173

# Encryption (for storing platform credentials)
ENCRYPTION_KEY=                 # Fernet key — generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 10. CODING STANDARDS

- Type hints on all function signatures
- Docstring on all classes and public methods
- All Claude calls through ai/claude.py only
- All WP API calls through platforms/wordpress/client.py only
- All Shopify API calls through platforms/shopify/client.py only
- Platform credentials always decrypted in memory, never logged
- All DB operations via SQLAlchemy ORM
- Celery tasks are thin wrappers — business logic lives in agent classes
- Log all agent actions with Python logging (structlog preferred)
- Frontend API calls always go through src/api/ modules — no inline fetch calls in components

---

## 11. BUILD ORDER

Complete each phase fully. Tick items in PROGRESS.md as you go.

### Phase 1 — Foundation
- [ ] Full folder structure created
- [ ] requirements.txt + package.json populated
- [ ] .env.example created
- [ ] docker-compose.yml (dev) working: db, redis, api, worker, frontend all start
- [ ] docker-compose.prod.yml (prod) written
- [ ] All Dockerfiles written
- [ ] db/models.py — all models
- [ ] Alembic configured + initial migration runs clean inside Docker
- [ ] config.py — all settings
- [ ] README.md — docker dev setup instructions

### Phase 2 — AI + Context Layer
- [ ] ai/claude.py
- [ ] ai/context_builder.py
- [ ] All prompt files stubbed with clear placeholder comments

### Phase 3 — Director Agent
- [ ] agents/base.py
- [ ] agents/director.py
- [ ] tasks/celery_app.py
- [ ] tasks/pipeline_tasks.py (stub — one task per agent)
- [ ] Test: director analyzes a brief, creates project + tasks in DB

### Phase 4 — Content Agent + Approval Gate
- [ ] agents/shared/content_agent.py
- [ ] api/routes/approvals.py
- [ ] api/websocket.py
- [ ] Test: content generated for a full brief, gate created, approve via API

### Phase 5 — Media + SEO Agents
- [ ] agents/shared/media_agent.py (Unsplash integration)
- [ ] agents/shared/seo_agent.py
- [ ] db/project_media table working
- [ ] Tests passing

### Phase 6 — WordPress Pipeline
- [ ] platforms/wordpress/client.py
- [ ] platforms/wordpress/wpcli.py
- [ ] platforms/wordpress/templates.py
- [ ] agents/wordpress/structure_agent.py
- [ ] agents/wordpress/builder_agent.py
- [ ] agents/wordpress/qa_agent.py
- [ ] End-to-end test against a real staging WordPress install

### Phase 7 — Shopify Pipeline
- [ ] platforms/shopify/client.py
- [ ] platforms/shopify/templates.py
- [ ] agents/shopify/structure_agent.py
- [ ] agents/shopify/builder_agent.py
- [ ] agents/shopify/theme_agent.py
- [ ] agents/shopify/qa_agent.py
- [ ] End-to-end test against a real Shopify dev store

### Phase 8 — Full API Layer
- [ ] All FastAPI routes complete
- [ ] Pydantic schemas complete
- [ ] WebSocket live updates working
- [ ] API authentication (SECRET_KEY header)

### Phase 9 — Frontend GUI
- [ ] Vite + React + Tailwind working inside Docker
- [ ] All pages scaffolded
- [ ] Dashboard with real data
- [ ] New Project form submits to API
- [ ] Project Detail with pipeline stepper + live WebSocket updates
- [ ] Content Review inline editing + approve
- [ ] Approval Queue page
- [ ] Settings page with credential testing

### Phase 10 — Documentation + Hardening
- [ ] docs/ all written
- [ ] All tests passing
- [ ] Prod docker-compose tested
- [ ] Nginx config + SSL working

---

## 12. SESSION HANDOFF PROTOCOL

At the END of every coding session, update PROGRESS.md:

```markdown
## Last Updated
[ISO timestamp] by [model name]

## Current Phase
Phase X — [name]

## Completed This Session
- [x] item

## In Progress
- [ ] item — sub-tasks done/remaining

## Decisions Made
- [decision and reason]

## Blockers
- [unresolved issues]

## Files Modified
- path/file.py — what changed

## Next Session Starts With
[Exact instruction]
```

---

*MASTER_PROMPT.md — do not modify between sessions.*
*Only PROGRESS.md changes.*
