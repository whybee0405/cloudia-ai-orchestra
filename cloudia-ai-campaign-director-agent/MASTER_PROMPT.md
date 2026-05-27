# CloudIA Content & Marketing Agent System — Master Project Prompt
# For use with: Claude Code / Codex / GitHub Copilot (Sonnet)
# Version: 1.0 | Owner: CloudIA
# Sister systems: google_ads_agents / cloudia-website-agents

---

## HOW TO USE THIS FILE

Paste MASTER_PROMPT.md + PROGRESS.md at the start of every session.
Model reads both, picks up exactly where last session ended.
At session end: model updates PROGRESS.md before closing.
Never re-architect. Never rename. Deviations documented in PROGRESS.md under Decisions Made.

---

## 1. PROJECT BRIEF

**Company:** CloudIA — South African digital agency serving SMEs.

**What we are building:**
A full multi-agent content creation and marketing system. It handles the complete
lifecycle: campaign planning → content creation (text, images, video) →
editing and brand consistency → human approval → scheduling → publishing →
analytics. It is operated internally by CloudIA on behalf of clients.
Clients authorise CloudIA's app via OAuth per platform — their tokens,
their accounts, clean separation.

**Core principles:**
- Director orchestrates. Agents execute. Humans approve before anything publishes.
- Every asset is client-specific — brand guidelines enforced on every output.
- Platform priority: Instagram, Facebook, WhatsApp Business, Google Business
  first. LinkedIn, TikTok second. YouTube, Twitter/X third.
- OAuth Option B: per-client tokens per platform. Never shared credentials.
- Docker on dev and prod. Same as sister systems.
- Lightweight React GUI — operator-focused, not decorative.
- Runs comfortably on same VPS as sister systems (add RAM if needed).

---

## 2. TECH STACK (exact — do not substitute)

### Backend
| Tool | Version | Purpose |
|---|---|---|
| Python | 3.11+ | All agents and API |
| FastAPI | 0.111 | REST API + WebSocket |
| SQLAlchemy | 2.0 | ORM |
| Alembic | 1.13 | Migrations |
| Celery | 5.3 | Async task queue |
| Celery Beat | 5.3 | Scheduled publishing jobs |
| Redis | 7 | Celery broker + result backend |
| PostgreSQL | 15 | Primary database |
| anthropic | 0.26.0 | Claude Sonnet — all reasoning and text |
| openai | 1.30 | DALL-E 3 image generation |
| replicate | 0.25 | Flux image generation (fallback) |
| elevenlabs | 1.2 | Text-to-speech voiceover |
| httpx | 0.27 | Async HTTP for platform APIs |
| Pillow | 10.3 | Image processing and resizing |
| minio | 7.2 | MinIO object storage client |
| cryptography | 42.0 | Fernet encryption for OAuth tokens |
| python-dotenv | 1.0 | Env management |
| ruff | 0.4 | Linting |
| pytest | 8.2 | Testing |

### Frontend
| Tool | Version | Purpose |
|---|---|---|
| React | 18 | UI |
| Vite | 5 | Build tool |
| Tailwind CSS | 3 | Styling |
| React Query | 5 | Server state |
| React Router | 6 | Routing |
| Axios | 1.7 | API calls |
| Lucide React | 0.383 | Icons |
| react-big-calendar | 1.13 | Content calendar view |

### Infrastructure
| Tool | Purpose |
|---|---|
| Docker + Compose | Dev and prod |
| MinIO | S3-compatible media file storage |
| ffmpeg | Video assembly and editing (system package) |
| Nginx | Reverse proxy (prod) |
| Certbot | SSL (prod) |

---

## 3. FOLDER STRUCTURE

```
cloudia-content-agents/
│
├── docker/
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   ├── Dockerfile.frontend
│   ├── nginx/
│   │   └── nginx.conf
│   ├── docker-compose.yml          # Dev
│   └── docker-compose.prod.yml     # Prod
│
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── worker.py                   # Celery + Beat entry point
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseAgent — logging, token tracking, error handling
│   │   ├── director.py             # Campaign Director — orchestrates full pipeline
│   │   ├── planner.py              # Content Planner — builds content calendar from brief
│   │   │
│   │   ├── text/
│   │   │   ├── __init__.py
│   │   │   ├── copywriter.py       # Captions, posts, social copy per platform
│   │   │   ├── seo_content.py      # Long-form blog articles, keyword-optimised
│   │   │   └── ad_copy.py          # Paid social and Google ad copy variants
│   │   │
│   │   ├── image/
│   │   │   ├── __init__.py
│   │   │   ├── generator.py        # DALL-E 3 / Flux AI image generation
│   │   │   ├── sourcing.py         # Unsplash / Pexels stock image sourcing
│   │   │   └── graphic_design.py   # Canva API branded template creation
│   │   │
│   │   ├── video/
│   │   │   ├── __init__.py
│   │   │   ├── script.py           # Video scripts + storyboards
│   │   │   ├── voiceover.py        # ElevenLabs TTS
│   │   │   ├── broll.py            # Pexels Video API stock footage sourcing
│   │   │   └── assembly.py         # ffmpeg: combine clips + audio + subs + overlays
│   │   │
│   │   ├── editing/
│   │   │   ├── __init__.py
│   │   │   ├── image_editor.py     # Crop, resize, filter, brand overlay via Pillow
│   │   │   ├── video_editor.py     # ffmpeg: cuts, transitions, colour grade, subtitles
│   │   │   ├── caption.py          # Auto-subtitle generation for all video
│   │   │   └── brand_consistency.py # Enforces brand guidelines on every asset
│   │   │
│   │   └── publishing/
│   │       ├── __init__.py
│   │       ├── formatter.py        # Reformats assets to per-platform specs
│   │       ├── scheduler.py        # Optimal time planning per platform
│   │       ├── publisher.py        # Posts via social APIs
│   │       └── analytics.py        # Pulls performance data post-publish
│   │
│   ├── platforms/
│   │   ├── __init__.py
│   │   ├── base.py                 # BasePlatform — OAuth token management
│   │   ├── meta.py                 # Facebook + Instagram + WhatsApp (Meta Graph API)
│   │   ├── google.py               # Google Business + YouTube (Google APIs)
│   │   ├── linkedin.py             # LinkedIn Marketing API
│   │   ├── tiktok.py               # TikTok Business API
│   │   └── twitter.py              # X API v2
│   │
│   ├── media/
│   │   ├── __init__.py
│   │   ├── storage.py              # MinIO client wrapper — upload, download, sign URLs
│   │   ├── ffmpeg_ops.py           # All ffmpeg commands wrapped as Python functions
│   │   └── image_ops.py            # All Pillow operations
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── claude.py               # Anthropic wrapper (same as sister systems)
│   │   ├── dalle.py                # OpenAI DALL-E 3 wrapper
│   │   ├── replicate_client.py     # Flux via Replicate (fallback)
│   │   ├── elevenlabs_client.py    # ElevenLabs TTS wrapper
│   │   ├── context_builder.py      # Client + campaign context for every prompt
│   │   └── prompts/
│   │       ├── __init__.py
│   │       ├── director.py
│   │       ├── planner.py
│   │       ├── copywriter.py
│   │       ├── seo_content.py
│   │       ├── ad_copy.py
│   │       ├── image_generator.py
│   │       ├── video_script.py
│   │       ├── brand_consistency.py
│   │       ├── caption.py
│   │       ├── formatter.py
│   │       └── analytics.py
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── session.py
│   │   └── migrations/
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── websocket.py
│   │   ├── schemas.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── campaigns.py
│   │       ├── calendar.py
│   │       ├── assets.py
│   │       ├── content.py
│   │       ├── approvals.py
│   │       ├── publishing.py
│   │       ├── analytics.py
│   │       ├── oauth.py            # OAuth initiation + callback routes
│   │       └── settings.py
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── celery_app.py
│   │   ├── pipeline_tasks.py       # Celery tasks per agent
│   │   └── scheduled_tasks.py      # Celery Beat — publishing scheduler
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
│   │   │   ├── client.js
│   │   │   ├── campaigns.js
│   │   │   ├── assets.js
│   │   │   ├── calendar.js
│   │   │   ├── approvals.js
│   │   │   ├── publishing.js
│   │   │   └── analytics.js
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── NewCampaign.jsx
│   │   │   ├── CampaignDetail.jsx
│   │   │   ├── ContentCalendar.jsx
│   │   │   ├── AssetLibrary.jsx
│   │   │   ├── ContentReview.jsx
│   │   │   ├── Scheduler.jsx
│   │   │   ├── Analytics.jsx
│   │   │   ├── PlatformAccounts.jsx
│   │   │   ├── BrandGuidelines.jsx
│   │   │   └── Settings.jsx
│   │   ├── components/
│   │   │   ├── PipelineStatus.jsx
│   │   │   ├── AssetCard.jsx
│   │   │   ├── AssetPreview.jsx
│   │   │   ├── CalendarView.jsx
│   │   │   ├── PlatformBadge.jsx
│   │   │   ├── ApprovalCard.jsx
│   │   │   ├── BrandGuidelinesEditor.jsx
│   │   │   ├── OAuthConnectButton.jsx
│   │   │   ├── AnalyticsChart.jsx
│   │   │   └── StatusBadge.jsx
│   │   └── hooks/
│   │       ├── useCampaignStatus.js
│   │       ├── useAssets.js
│   │       └── useAnalytics.js
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
│   │   ├── mock_dalle.py
│   │   ├── mock_elevenlabs.py
│   │   ├── mock_meta.py
│   │   ├── mock_linkedin.py
│   │   ├── mock_tiktok.py
│   │   ├── mock_google.py
│   │   └── mock_minio.py
│   ├── test_director.py
│   ├── test_planner.py
│   ├── test_copywriter.py
│   ├── test_image_generator.py
│   ├── test_video_assembly.py
│   ├── test_brand_consistency.py
│   ├── test_formatter.py
│   ├── test_publisher.py
│   ├── test_scheduler.py
│   ├── test_oauth.py
│   ├── test_analytics.py
│   └── test_api.py
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── AGENT_SPECS.md
│   ├── DATABASE.md
│   ├── PLATFORM_SPECS.md           # Per-platform content format requirements
│   ├── OAUTH_SETUP.md              # How to configure each platform OAuth app
│   ├── DOCKER.md
│   └── DECISIONS.md
│
├── MASTER_PROMPT.md
├── PROGRESS.md
├── STRESS_TEST_PROMPT.md
├── .env.example
├── .gitignore
└── README.md
```

---

## 4. DOCKER CONFIGURATION

### docker-compose.yml (DEV)
```yaml
version: '3.9'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: cloudia_content
      POSTGRES_USER: cloudia
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5433:5432"              # 5433 to avoid conflict with sister systems

  redis:
    image: redis:7-alpine
    ports:
      - "6380:6379"              # 6380 to avoid conflict

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"              # S3 API
      - "9001:9001"              # MinIO Console (dev only)

  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    command: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend:/app/backend
    ports:
      - "8001:8000"              # 8001 to avoid conflict
    env_file: .env
    environment:
      - DATABASE_URL=postgresql://cloudia:${DB_PASSWORD}@db:5432/cloudia_content
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
    depends_on: [db, redis, minio]

  worker:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    command: celery -A backend.tasks.celery_app worker --loglevel=info -Q content,publishing,analytics
    volumes:
      - ./backend:/app/backend
    env_file: .env
    environment:
      - DATABASE_URL=postgresql://cloudia:${DB_PASSWORD}@db:5432/cloudia_content
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
    depends_on: [db, redis, minio]

  beat:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    command: celery -A backend.tasks.celery_app beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    volumes:
      - ./backend:/app/backend
    env_file: .env
    environment:
      - DATABASE_URL=postgresql://cloudia:${DB_PASSWORD}@db:5432/cloudia_content
      - REDIS_URL=redis://redis:6379/0
    depends_on: [db, redis]

  frontend:
    build:
      context: ./frontend
      dockerfile: ../docker/Dockerfile.frontend
    command: npm run dev -- --host
    volumes:
      - ./frontend/src:/app/src
    ports:
      - "5174:5173"              # 5174 to avoid conflict
    environment:
      - VITE_API_URL=http://localhost:8001

volumes:
  postgres_data:
  minio_data:
```

### docker-compose.prod.yml (PROD)
```yaml
version: '3.9'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: cloudia_content
      POSTGRES_USER: cloudia
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  minio:
    image: minio/minio:latest
    command: server /data
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes:
      - minio_data:/data
    restart: unless-stopped
    # No ports exposed — access via internal network only

  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    command: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2
    env_file: .env.prod
    environment:
      - DATABASE_URL=postgresql://cloudia:${DB_PASSWORD}@db:5432/cloudia_content
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
    depends_on: [db, redis, minio]
    restart: unless-stopped

  worker:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    command: celery -A backend.tasks.celery_app worker --loglevel=warning -Q content,publishing,analytics --concurrency=4
    env_file: .env.prod
    environment:
      - DATABASE_URL=postgresql://cloudia:${DB_PASSWORD}@db:5432/cloudia_content
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
    depends_on: [db, redis, minio]
    restart: unless-stopped

  beat:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    command: celery -A backend.tasks.celery_app beat --loglevel=warning
    env_file: .env.prod
    depends_on: [db, redis]
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
    depends_on: [api, frontend]
    restart: unless-stopped

volumes:
  postgres_data:
  minio_data:
  certbot_certs:
```

### docker/Dockerfile.api
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY alembic.ini .

EXPOSE 8000
```

Note: ffmpeg installed at image level — all video operations available in both api and worker containers.

---

## 5. DATABASE SCHEMA

### clients
Reuse from cloudia-website-agents if running in shared DB.
If separate DB, replicate the same model exactly.

### campaigns
```sql
id                  SERIAL PRIMARY KEY
client_id           INTEGER REFERENCES clients(id)
name                VARCHAR(255) NOT NULL
goal                TEXT                -- 'brand_awareness' | 'lead_gen' | 'product_launch' | 'engagement'
status              VARCHAR(30) DEFAULT 'planned'
                    -- planned | calendar_review | creating | editing
                    -- awaiting_approval | scheduled | active | completed | paused | failed
brief               JSONB NOT NULL
platforms           JSONB NOT NULL      -- ["instagram", "facebook", "whatsapp", "google_business"]
duration_days       INTEGER
start_date          DATE
end_date            DATE
posts_per_week      INTEGER
content_mix         JSONB
                    -- { "image_posts": 3, "reels": 2, "stories": 5, "articles": 1 }
target_audience     TEXT
campaign_hashtags   JSONB               -- ["#tag1", "#tag2"]
created_at          TIMESTAMP DEFAULT NOW()
completed_at        TIMESTAMP
operator_notes      TEXT
```

### content_calendar
One row per planned post in the campaign.

```sql
id                  SERIAL PRIMARY KEY
campaign_id         INTEGER REFERENCES campaigns(id)
client_id           INTEGER REFERENCES clients(id)
platform            VARCHAR(50) NOT NULL
                    -- instagram | facebook | tiktok | linkedin | twitter
                    -- youtube | google_business | whatsapp | wordpress_blog
content_type        VARCHAR(50) NOT NULL
                    -- image_post | carousel | reel | story | short_video
                    -- long_video | article | ad | whatsapp_broadcast
scheduled_for       TIMESTAMP NOT NULL
status              VARCHAR(30) DEFAULT 'planned'
                    -- planned | creating | created | editing | edited
                    -- awaiting_approval | approved | scheduled | published | failed
asset_id            INTEGER REFERENCES content_assets(id)
topic               TEXT                -- what this specific post is about
notes               TEXT
created_at          TIMESTAMP DEFAULT NOW()
```

### content_assets
Every piece of created content — text, image, or video.

```sql
id                  SERIAL PRIMARY KEY
campaign_id         INTEGER REFERENCES campaigns(id)
client_id           INTEGER REFERENCES clients(id)
asset_type          VARCHAR(20) NOT NULL    -- 'text' | 'image' | 'video' | 'audio'
content_type        VARCHAR(50)             -- 'caption' | 'article' | 'script' | 'ad_copy'
                                            -- 'generated_image' | 'stock_image' | 'reel'
                                            -- 'short_video' | 'voiceover' | 'carousel'
title               VARCHAR(255)
text_content        TEXT                    -- for text assets
storage_path        TEXT                    -- MinIO path for media assets
storage_bucket      VARCHAR(100)
file_size_bytes     BIGINT
duration_seconds    INTEGER                 -- for video/audio
width               INTEGER                 -- for image/video
height              INTEGER                 -- for image/video
format              VARCHAR(20)             -- 'mp4' | 'jpg' | 'png' | 'webp' | 'mp3'
platform_versions   JSONB
-- {
--   "instagram": { "path": "...", "width": 1080, "height": 1080 },
--   "tiktok":    { "path": "...", "width": 1080, "height": 1920 }
-- }
status              VARCHAR(30) DEFAULT 'draft'
                    -- draft | editing | brand_check | approved | published | archived
brand_check_passed  BOOLEAN
brand_check_notes   TEXT
generation_prompt   TEXT                    -- prompt used to create this asset
generation_model    VARCHAR(100)            -- 'dall-e-3' | 'flux' | 'claude-sonnet'
tokens_used         INTEGER
cost_usd            NUMERIC(8,6)
created_by_agent    VARCHAR(100)
created_at          TIMESTAMP DEFAULT NOW()
```

### asset_versions
Full edit history per asset.

```sql
id                  SERIAL PRIMARY KEY
asset_id            INTEGER REFERENCES content_assets(id)
version_number      INTEGER NOT NULL
storage_path        TEXT
change_description  TEXT
changed_by_agent    VARCHAR(100)
created_at          TIMESTAMP DEFAULT NOW()
```

### brand_guidelines
Per-client rules enforced by Brand Consistency Agent on every asset.

```sql
id                  SERIAL PRIMARY KEY
client_id           INTEGER REFERENCES clients(id) UNIQUE
primary_colour      VARCHAR(7)              -- hex
secondary_colour    VARCHAR(7)
accent_colour       VARCHAR(7)
background_colour   VARCHAR(7)
logo_path           TEXT                    -- MinIO path to logo
logo_dark_path      TEXT                    -- dark version
heading_font        VARCHAR(100)
body_font           VARCHAR(100)
tone_keywords       JSONB                   -- ["professional", "warm", "trustworthy"]
forbidden_words     JSONB                   -- words never to use
competitor_names    JSONB                   -- never mention these
required_elements   JSONB
-- {
--   "logo_on_all_images": true,
--   "hashtags_required": ["#brandtag"],
--   "watermark": true,
--   "cta_required": true
-- }
image_style_notes   TEXT
copy_style_notes    TEXT
updated_at          TIMESTAMP DEFAULT NOW()
```

### platform_accounts
OAuth tokens per client per platform. All token fields encrypted at rest.

```sql
id                  SERIAL PRIMARY KEY
client_id           INTEGER REFERENCES clients(id)
platform            VARCHAR(50) NOT NULL
                    -- instagram | facebook | tiktok | linkedin
                    -- twitter | youtube | google_business | whatsapp
account_name        VARCHAR(255)            -- display name of the account
account_id          VARCHAR(255)            -- platform's internal account ID
page_id             VARCHAR(255)            -- for Facebook/Instagram (Page ID)
access_token        TEXT                    -- encrypted
refresh_token       TEXT                    -- encrypted
token_expires_at    TIMESTAMP
scopes              JSONB                   -- granted OAuth scopes
is_active           BOOLEAN DEFAULT TRUE
last_verified_at    TIMESTAMP
connected_at        TIMESTAMP DEFAULT NOW()
UNIQUE(client_id, platform, account_id)
```

### scheduled_posts
Approved content waiting to be published at a specific time.

```sql
id                  SERIAL PRIMARY KEY
calendar_id         INTEGER REFERENCES content_calendar(id)
asset_id            INTEGER REFERENCES content_assets(id)
platform_account_id INTEGER REFERENCES platform_accounts(id)
scheduled_for       TIMESTAMP NOT NULL
caption             TEXT
hashtags            JSONB
first_comment       TEXT                    -- Instagram first comment hashtags strategy
status              VARCHAR(20) DEFAULT 'queued'
                    -- queued | publishing | published | failed | cancelled
celery_task_id      VARCHAR(255)
created_at          TIMESTAMP DEFAULT NOW()
```

### published_posts
Record of every live post across all platforms.

```sql
id                  SERIAL PRIMARY KEY
scheduled_post_id   INTEGER REFERENCES scheduled_posts(id)
platform            VARCHAR(50)
platform_post_id    VARCHAR(255)            -- ID returned by platform API
post_url            TEXT
published_at        TIMESTAMP
raw_response        JSONB                   -- full platform API response
```

### post_analytics
Performance data pulled after publish. Three snapshots: 24h, 72h, 7d.

```sql
id                  SERIAL PRIMARY KEY
published_post_id   INTEGER REFERENCES published_posts(id)
snapshot_type       VARCHAR(20)             -- '24h' | '72h' | '7d' | '30d'
pulled_at           TIMESTAMP
impressions         BIGINT
reach               BIGINT
likes               INTEGER
comments            INTEGER
shares              INTEGER
saves               INTEGER
clicks              INTEGER
video_views         BIGINT
video_watch_time_sec BIGINT
engagement_rate     NUMERIC(6,4)
platform_raw        JSONB                   -- full platform analytics response
```

### agent_tasks
Same pattern as sister systems.

```sql
id                  SERIAL PRIMARY KEY
campaign_id         INTEGER REFERENCES campaigns(id)
calendar_id         INTEGER REFERENCES content_calendar(id)
agent_name          VARCHAR(100)
pipeline_order      INTEGER
status              VARCHAR(20) DEFAULT 'pending'
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
Same pattern as sister systems.

```sql
id                  SERIAL PRIMARY KEY
campaign_id         INTEGER REFERENCES campaigns(id)
gate_name           VARCHAR(100)
                    -- 'calendar_review' | 'content_batch_review' | 'final_publish_approval'
pipeline_order      INTEGER
status              VARCHAR(20) DEFAULT 'pending'
notes               TEXT
created_at          TIMESTAMP DEFAULT NOW()
reviewed_at         TIMESTAMP
reviewed_by         VARCHAR(100)
```

---

## 6. PLATFORM CONTENT SPECIFICATIONS

### docs/PLATFORM_SPECS.md content (build this file)
Formatter Agent uses these to resize and reformat every asset.

```python
# backend/config.py — PLATFORM_SPECS constant

PLATFORM_SPECS = {
    "instagram": {
        "image_post":  {"width": 1080, "height": 1080, "format": "jpg", "max_mb": 8},
        "portrait":    {"width": 1080, "height": 1350, "format": "jpg", "max_mb": 8},
        "landscape":   {"width": 1080, "height": 566,  "format": "jpg", "max_mb": 8},
        "story":       {"width": 1080, "height": 1920, "format": "jpg", "max_mb": 30},
        "reel":        {"width": 1080, "height": 1920, "format": "mp4",
                        "max_mb": 650, "max_seconds": 90, "min_seconds": 3},
        "carousel":    {"width": 1080, "height": 1080, "format": "jpg",
                        "max_slides": 10},
        "caption_max_chars": 2200,
        "hashtag_max": 30,
    },
    "facebook": {
        "image_post":  {"width": 1200, "height": 630, "format": "jpg", "max_mb": 8},
        "story":       {"width": 1080, "height": 1920, "format": "jpg", "max_mb": 30},
        "reel":        {"width": 1080, "height": 1920, "format": "mp4",
                        "max_mb": 1000, "max_seconds": 90},
        "video":       {"width": 1280, "height": 720, "format": "mp4",
                        "max_mb": 10240, "max_seconds": 14400},
        "caption_max_chars": 63206,
    },
    "tiktok": {
        "video":       {"width": 1080, "height": 1920, "format": "mp4",
                        "max_mb": 287, "min_seconds": 3, "max_seconds": 600},
        "caption_max_chars": 2200,
        "hashtag_max": 5,
    },
    "linkedin": {
        "image_post":  {"width": 1200, "height": 627, "format": "jpg", "max_mb": 5},
        "video":       {"width": 1920, "height": 1080, "format": "mp4",
                        "max_mb": 5120, "max_seconds": 600},
        "caption_max_chars": 3000,
    },
    "twitter": {
        "image_post":  {"width": 1600, "height": 900, "format": "jpg", "max_mb": 5},
        "video":       {"width": 1280, "height": 720, "format": "mp4",
                        "max_mb": 512, "max_seconds": 140},
        "caption_max_chars": 280,
    },
    "youtube": {
        "video":       {"width": 1920, "height": 1080, "format": "mp4",
                        "max_mb": 256000, "max_seconds": 43200},
        "short":       {"width": 1080, "height": 1920, "format": "mp4",
                        "max_mb": 256000, "max_seconds": 60},
        "thumbnail":   {"width": 1280, "height": 720, "format": "jpg", "max_mb": 2},
        "description_max_chars": 5000,
    },
    "google_business": {
        "image_post":  {"width": 720, "height": 540, "format": "jpg",
                        "min_width": 400, "min_height": 300, "max_mb": 5},
        "caption_max_chars": 1500,
    },
    "whatsapp": {
        "image":       {"format": "jpg", "max_mb": 5},
        "video":       {"format": "mp4", "max_mb": 64, "max_seconds": 90},
        "message_max_chars": 4096,
    },
}
```

---

## 7. AGENT SPECIFICATIONS

### Director Agent (agents/director.py)
**Trigger:** New campaign created via GUI
**Role:** Validates brief, identifies content mix, kicks off Planner

```
Steps:
  1. Load client profile + brand guidelines
  2. Validate: all required platforms have OAuth tokens (platform_accounts active)
  3. Validate: campaign brief has enough info to proceed
  4. If validation fails: return specific missing items to operator
  5. Call Claude with full context:
     "Given this brief, what content mix makes sense for these platforms?"
  6. Write campaign to DB (status: planning)
  7. Queue: planner_agent
```

### Content Planner Agent (agents/planner.py)
**Trigger:** Director queues it
**Role:** Builds the full content calendar

```
Steps:
  1. Load campaign brief + client context + platform specs
  2. Call Claude:
     For each week in campaign duration:
       What posts, what platform, what type, what topic?
     Return: structured calendar JSON
  3. Write content_calendar rows (one per planned post)
  4. Create ApprovalGate: 'calendar_review' (status: pending)
  5. Notify operator

Human reviews calendar:
  - Reschedule individual items
  - Delete items
  - Add items
  - Approve → creation begins
```

### Copywriter Agent (agents/text/copywriter.py)
**Trigger:** calendar item with content_type: image_post, story, carousel, reel
**Role:** Writes caption, hashtags, first_comment, CTA for each post

```
Steps per calendar item:
  1. Load client context + brand guidelines + platform specs
  2. Load topic from calendar item
  3. Call Claude:
     "Write a [platform] [content_type] caption for [client] about [topic].
      Tone: [tone]. Max chars: [platform limit]. Include CTA: [goal].
      Brand hashtags: [required]. Forbidden words: [list]."
  4. Validate output:
     - Under character limit for platform
     - Contains required brand hashtags
     - No forbidden words
     - CTA present
  5. Store to content_assets (asset_type: text)
  6. Link to calendar item
```

### SEO Content Agent (agents/text/seo_content.py)
**Trigger:** calendar item with content_type: article
**Role:** Full long-form blog article — keyword-optimised

```
Steps:
  1. Load client context + SEO target keyword from calendar item
  2. Call Claude:
     - Generate article outline
     - Write full article (800–2000 words depending on brief)
     - Write meta title + meta description
     - Write excerpt for social promotion
  3. Validate: meta title under 60 chars, meta desc under 160
  4. Store to content_assets
```

### Ad Copy Agent (agents/text/ad_copy.py)
**Trigger:** calendar item with content_type: ad
**Role:** Multiple copy variants for A/B testing

```
Steps:
  1. Load campaign goal + target audience + platform
  2. Call Claude:
     Generate 3 variants per ad:
       - Headline (platform-specific char limits)
       - Body copy
       - CTA button text
  3. Store each variant as separate content_asset
  4. Link all variants to calendar item
```

### Image Generator Agent (agents/image/generator.py)
**Trigger:** calendar item requiring an AI-generated image
**Role:** Creates image via DALL-E 3 or Flux fallback

```
Steps:
  1. Load client context + brand guidelines + topic
  2. Call Claude to generate a DALL-E prompt:
     "Write a DALL-E 3 prompt for a [content_type] image for [client].
      Style: [brand aesthetic]. Topic: [topic]. Avoid: [forbidden elements]."
  3. Call DALL-E 3 API with generated prompt
  4. If DALL-E fails or is unavailable: fall back to Replicate (Flux)
  5. Download image → upload to MinIO
  6. Store to content_assets with generation_prompt + model
  7. Queue: image_editor_agent for brand overlay
```

### Image Sourcing Agent (agents/image/sourcing.py)
**Trigger:** calendar item requiring stock photography
**Role:** Finds relevant stock image from Unsplash or Pexels

```
Steps:
  1. Load topic from calendar item
  2. Call Claude: "Generate 3 search query variations for [topic] stock photo"
  3. Try Unsplash first (50 req/hour free)
  4. Fall back to Pexels (200 req/hour free)
  5. Select best match
  6. Download + upload to MinIO
  7. Store attribution (mandatory for Unsplash/Pexels licensing)
  8. Queue: image_editor_agent
```

### Graphic Design Agent (agents/image/graphic_design.py)
**Trigger:** calendar item requiring branded template (quote cards, announcements, etc.)
**Role:** Creates on-brand designed image via Canva API

```
Steps:
  1. Load brand guidelines (colours, fonts, logo)
  2. Select appropriate Canva template per content_type
  3. Populate template via Canva API:
     - Replace text placeholders with generated copy
     - Apply brand colours
     - Insert logo
  4. Export image via Canva API
  5. Upload to MinIO
  6. Store to content_assets

Note: Requires Canva API access (Enterprise plan or API beta).
If unavailable: fallback to Image Generator Agent with brand overlay.
```

### Script Agent (agents/video/script.py)
**Trigger:** calendar item requiring video
**Role:** Full video script + storyboard

```
Steps:
  1. Load client context + topic + video duration target
  2. Call Claude:
     Return JSON:
     {
       "title": "...",
       "hook": "...",                    -- first 3 seconds
       "scenes": [
         { "duration_sec": 5, "visual": "...", "voiceover": "...", "text_overlay": "..." }
       ],
       "cta": "...",
       "total_duration_sec": 30
     }
  3. Validate total duration within platform spec
  4. Store script JSON to content_assets
  5. Queue: voiceover_agent + broll_agent (parallel)
```

### Voiceover Agent (agents/video/voiceover.py)
**Trigger:** Script agent completes
**Role:** Generates audio narration via ElevenLabs

```
Steps:
  1. Load script (voiceover text per scene)
  2. Load client voice preference from brand_guidelines
     (voice_id, stability, similarity_boost)
  3. Call ElevenLabs API per scene
  4. Upload audio files to MinIO
  5. Store to content_assets (asset_type: audio)
  6. When voiceover + broll both complete → queue assembly_agent
```

### B-Roll Agent (agents/video/broll.py)
**Trigger:** Script agent completes (parallel with voiceover)
**Role:** Sources stock video clips per scene from Pexels Video API

```
Steps:
  1. Load script scenes
  2. For each scene: generate search query from visual description
  3. Call Pexels Video API
  4. Download clip matching scene duration
  5. Upload to MinIO
  6. Store clip paths + scene mapping to content_assets
  7. When voiceover + broll both complete → queue assembly_agent
```

### Video Assembly Agent (agents/video/assembly.py)
**Trigger:** Voiceover + B-Roll both complete
**Role:** Assembles final video via ffmpeg

```
Steps:
  1. Load script JSON, audio paths, clip paths from MinIO
  2. For each scene, ffmpeg:
     - Trim clip to scene duration
     - Overlay voiceover audio
     - Add text overlay (heading/CTA) with brand font + colour
  3. Concatenate all scenes
  4. Add brand intro (2 sec logo animation if exists)
  5. Add brand outro (logo + CTA + website)
  6. Add background music at 15% volume (royalty-free from assets library)
  7. Export master video (1920x1080 or 1080x1920 per platform target)
  8. Upload to MinIO
  9. Store to content_assets
  10. Queue: video_editor_agent
```

### Image Editor Agent (agents/editing/image_editor.py)
**Trigger:** Image asset created
**Role:** Applies brand overlays, resizes for all target platforms

```
Steps per image:
  1. Load brand guidelines (logo, colours, watermark setting)
  2. If required: overlay logo (bottom-right, 10% width, 80% opacity)
  3. If required: add brand colour banner at bottom with CTA text
  4. For each target platform: resize/crop to platform spec (from PLATFORM_SPECS)
  5. Upload all platform versions to MinIO
  6. Store platform_versions JSON to content_asset
  7. Queue: brand_consistency_agent
```

### Video Editor Agent (agents/editing/video_editor.py)
**Trigger:** Assembly agent completes
**Role:** Colour grading, transitions, subtitles, final export per platform

```
Steps:
  1. Load master video from MinIO
  2. Apply colour grade (LUT based on brand tone — warm/cool/neutral)
  3. Add transition effects between scenes (dissolve/cut/slide)
  4. Render subtitle track (from caption_agent output)
  5. Burn subtitles into video (for TikTok, Reels — autoplay without sound)
  6. For each target platform: resize + reformat per PLATFORM_SPECS
  7. Upload all versions to MinIO
  8. Queue: brand_consistency_agent
```

### Caption Agent (agents/editing/caption.py)
**Trigger:** Video assembly completes (parallel with video_editor)
**Role:** Auto-generates subtitle SRT file from voiceover audio

```
Steps:
  1. Load voiceover audio from MinIO
  2. Transcribe via OpenAI Whisper (whisper-1 model)
  3. Generate SRT file with timestamps
  4. Store SRT to MinIO
  5. Store path to content_asset
  6. Caption Agent output consumed by Video Editor for subtitle burn-in
```

### Brand Consistency Agent (agents/editing/brand_consistency.py)
**Trigger:** Every image or video after editing
**Role:** Final check before human approval gate

```
Checks per asset:
  Image:
    - Logo present if required_elements.logo_on_all_images = true
    - Brand colours used (not checked pixel-perfect, verified via metadata)
    - No competitor names in any text overlay
    - Required hashtags present in caption
    - CTA present if cta_required = true

  Video:
    - Brand intro/outro present
    - No competitor names in voiceover script
    - CTA in final 5 seconds

  Text (caption, article):
    - No forbidden_words present
    - Tone matches tone_keywords (send to Claude for classification)
    - Under character limit for platform
    - Required hashtags included

Output:
  { passed: bool, issues: [{ field, issue, severity }] }
  If passed: asset status → approved_for_review
  If failed (any HIGH severity): asset status → brand_check_failed, notify operator
  If only warnings: passed with notes
```

### Platform Formatter Agent (agents/publishing/formatter.py)
**Trigger:** Asset approved by operator
**Role:** Creates platform-specific versions of every asset

```
Steps:
  1. Load approved asset
  2. Load target platforms from content_calendar item
  3. For each platform: read PLATFORM_SPECS
  4. If image: Pillow resize/crop to exact spec
  5. If video: ffmpeg transcode to exact spec (bitrate, codec, resolution)
  6. Validate output file size under platform limit
  7. Upload all formatted versions to MinIO
  8. Update asset.platform_versions with new paths
```

### Scheduler Agent (agents/publishing/scheduler.py)
**Trigger:** Formatter completes
**Role:** Determines optimal posting times per platform

```
Steps:
  1. Load calendar item's scheduled_for datetime
  2. If operator set a specific time: use it
  3. If set to "optimal": apply best-time rules:
     Instagram: Tue-Fri 8am-9am or 7pm-9pm SAST
     Facebook:  Wed-Fri 10am-3pm SAST
     TikTok:    Tue-Fri 7am-9am or 7pm-11pm SAST
     LinkedIn:  Tue-Thu 8am-10am SAST
     WhatsApp:  Mon-Fri 9am-11am SAST
  4. Write scheduled_post row (status: queued)
  5. Queue Celery Beat task at exact scheduled_for time
```

### Publisher Agent (agents/publishing/publisher.py)
**Trigger:** Celery Beat fires at scheduled_for time
**Role:** Posts to platform via API

```
Steps:
  1. Load scheduled_post + asset + platform_account
  2. Decrypt platform OAuth token
  3. Check token not expired — if expired: pause post, notify operator
  4. Upload media to platform (most platforms require server-side upload)
  5. Create post via platform API
  6. Store platform_post_id + post_url to published_posts
  7. Update calendar status → published
  8. Queue Analytics Agent tasks: 24h, 72h, 7d (delayed Celery tasks)
```

Platform-specific publisher methods:
```python
# platforms/meta.py
def publish_instagram_image(account, asset, caption, hashtags): ...
def publish_instagram_reel(account, asset, caption): ...
def publish_instagram_story(account, asset): ...
def publish_facebook_post(account, asset, caption): ...
def publish_whatsapp_broadcast(account, message, media_path): ...

# platforms/google.py
def publish_google_business_post(account, asset, caption): ...
def publish_youtube_video(account, asset, title, description, tags): ...

# platforms/linkedin.py
def publish_linkedin_post(account, asset, caption): ...

# platforms/tiktok.py
def publish_tiktok_video(account, asset, caption, hashtags): ...

# platforms/twitter.py
def publish_tweet(account, text, media_path): ...
```

### Analytics Agent (agents/publishing/analytics.py)
**Trigger:** 24h, 72h, 7d after publish (Celery Beat delayed tasks)
**Role:** Pulls performance data from each platform

```
Steps:
  1. Load published_post (platform, platform_post_id, platform_account)
  2. Call platform analytics API for this post ID
  3. Store to post_analytics (impressions, reach, likes, comments, shares, etc.)
  4. If 7d snapshot: calculate engagement_rate, flag over/underperforming posts
  5. Underperforming post (engagement_rate < industry baseline): notify operator
  6. Overperforming post (top 10% of campaign): flag as "content that works" for future reference
```

---

## 8. OAUTH ARCHITECTURE (Option B)

Each client authorises CloudIA's app per platform. Operator initiates from GUI.

### Flow per platform:
```
1. Operator clicks "Connect Instagram" for Client A in GUI
2. GUI calls: GET /oauth/initiate/{client_id}/instagram
3. Backend generates state token (stored in Redis with client_id, 10min TTL)
4. Backend returns OAuth URL with state parameter
5. Operator opens URL in browser (or redirects client)
6. User authorises on platform
7. Platform redirects to: GET /oauth/callback/instagram?code=...&state=...
8. Backend verifies state from Redis
9. Backend exchanges code for access_token + refresh_token
10. Tokens encrypted with Fernet, stored in platform_accounts
11. GUI shows: Connected ✓
```

### Token Refresh:
```python
# platforms/base.py
class BasePlatform:
    def get_valid_token(self, account: PlatformAccount) -> str:
        if account.token_expires_at < datetime.utcnow() + timedelta(minutes=5):
            return self.refresh_token(account)
        return decrypt(account.access_token)

    def refresh_token(self, account: PlatformAccount) -> str:
        # Platform-specific refresh logic
        # Update account in DB with new token + expiry
        raise NotImplementedError
```

### OAuth Redirect URIs to register per platform app:
```
https://your-domain.com/api/oauth/callback/instagram
https://your-domain.com/api/oauth/callback/facebook
https://your-domain.com/api/oauth/callback/whatsapp
https://your-domain.com/api/oauth/callback/linkedin
https://your-domain.com/api/oauth/callback/tiktok
https://your-domain.com/api/oauth/callback/youtube
https://your-domain.com/api/oauth/callback/google_business
https://your-domain.com/api/oauth/callback/twitter
```

---

## 9. MINIO STORAGE STRUCTURE

```
bucket: cloudia-media (created on first startup)

{client_id}/
  brand/
    logo.png
    logo_dark.png
    guidelines.json
  campaigns/
    {campaign_id}/
      raw/                        ← original sourced/generated assets
        images/
        videos/
        audio/
      edited/                     ← after editing agents
        images/
          {asset_id}_instagram.jpg
          {asset_id}_facebook.jpg
          {asset_id}_linkedin.jpg
        videos/
          {asset_id}_reel.mp4
          {asset_id}_tiktok.mp4
          {asset_id}_youtube.mp4
      published/                  ← copies of what was actually published
```

---

## 10. CONTEXT BUILDER (ai/context_builder.py)

```python
def build_campaign_context(client: Client, campaign: Campaign,
                           guidelines: BrandGuidelines) -> str:
    return f"""
=== CLIENT PROFILE ===
Business: {client.name}
Industry: {client.industry}
Location: {client.city}, South Africa
Target audience: {client.target_audience}
USP: {client.usp}

=== CAMPAIGN BRIEF ===
Campaign name: {campaign.name}
Goal: {campaign.goal}
Platforms: {', '.join(campaign.platforms)}
Duration: {campaign.duration_days} days
Content mix: {json.dumps(campaign.content_mix)}
Target audience for this campaign: {campaign.target_audience}
Campaign hashtags: {', '.join(campaign.campaign_hashtags or [])}
Additional brief: {json.dumps(campaign.brief, indent=2)}

=== BRAND GUIDELINES ===
Tone keywords: {', '.join(guidelines.tone_keywords or [])}
Forbidden words: {', '.join(guidelines.forbidden_words or [])}
Required hashtags: see required_elements
Copy style: {guidelines.copy_style_notes or 'Not specified'}
Image style: {guidelines.image_style_notes or 'Not specified'}
Required elements: {json.dumps(guidelines.required_elements or {})}

=== YOUR ROLE ===
You are a senior social media strategist and content creator at CloudIA,
a South African digital agency. You are creating content for this specific
client and campaign. All content must:
1. Match the tone keywords exactly
2. Never use forbidden words
3. Be written for a South African audience unless specified otherwise
4. Include required hashtags where applicable
5. Be truthful — never invent claims about the client's products or services
6. Where JSON output is required: return ONLY valid JSON, no markdown, no preamble
"""
```

---

## 11. ENVIRONMENT VARIABLES (.env.example)

```env
# Database
DB_PASSWORD=
DATABASE_URL=postgresql://cloudia:password@db:5432/cloudia_content

# Redis
REDIS_URL=redis://redis:6379/0

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ROOT_USER=
MINIO_ROOT_PASSWORD=
MINIO_BUCKET=cloudia-media
MINIO_SECURE=false           # true in prod with TLS

# AI APIs
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-20250514
OPENAI_API_KEY=              # DALL-E 3
REPLICATE_API_TOKEN=         # Flux fallback
ELEVENLABS_API_KEY=

# Media APIs
UNSPLASH_ACCESS_KEY=
PEXELS_API_KEY=
CANVA_API_KEY=               # Optional — Canva API beta

# Social Platform OAuth Apps
# Meta (covers Facebook + Instagram + WhatsApp)
META_APP_ID=
META_APP_SECRET=
# LinkedIn
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
# TikTok
TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=
# Twitter / X
TWITTER_CLIENT_ID=
TWITTER_CLIENT_SECRET=
# Google (covers YouTube + Google Business)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# App
OAUTH_CALLBACK_BASE_URL=https://your-domain.com/api
SECRET_KEY=
ENCRYPTION_KEY=              # Fernet — python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:5174

# Email
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
NOTIFICATION_FROM=

# Celery Beat (publishing schedule)
CELERY_TIMEZONE=Africa/Johannesburg
```

---

## 12. GUI SPECIFICATION

### Dashboard (/)
- Campaign cards: client, goal, status, platform icons, progress bar
- Stats: active campaigns, posts scheduled this week, posts published this month
- Content needing review (count badge)
- "New Campaign" button

### New Campaign (/campaigns/new)
Multi-step form:
```
Step 1: Select client (or create new)
Step 2: Campaign goal + name
Step 3: Platform selection (checkbox grid with platform icons)
Step 4: Duration + posting frequency
Step 5: Content mix (how many of each type per week)
Step 6: Target audience + brief
Step 7: Campaign hashtags
Step 8: Review + Launch
```

### Campaign Detail (/campaigns/:id)
- Status header: campaign name, client, platforms, date range
- Pipeline visual: Director → Planner → [Content] → [Edit] → [Approve] → [Publish]
- Content Calendar tab: monthly calendar view (react-big-calendar)
  Each event: platform icon, content type, status colour
- Assets tab: grid of all assets (thumbnail, type, status badge)
- Analytics tab: aggregate performance charts

### Content Calendar (/calendar)
- Full-page monthly view across ALL campaigns
- Drag to reschedule
- Click item → opens asset preview + approve/reject
- Filter by client, platform, status

### Asset Library (/assets)
- Grid view: thumbnail, type badge, platform badges, status
- Filter: client, campaign, type, platform, status
- Click: full preview (image viewer or video player)
- Actions: approve, request revision, download, archive

### Content Review (/campaigns/:id/review)
- Batch review interface
- One card per asset: preview + caption + hashtags
- Inline edit on caption/hashtags
- Approve / Request Revision / Reject per card
- Bulk approve button

### Scheduler (/scheduler)
- Timeline view: what posts, when, to which platform
- Status: queued (grey), publishing (yellow), published (green), failed (red)
- Manual reschedule drag
- Pause all button (emergency stop)

### Analytics (/analytics)
- Filter: client, campaign, platform, date range
- Cards: total reach, total impressions, total engagement, avg engagement rate
- Chart: reach over time per platform (line chart)
- Table: top performing posts (image thumbnail, platform, engagement rate)
- Export CSV button

### Platform Accounts (/accounts)
- Per client section
- Platform icons: connected (green tick) or not connected (grey + Connect button)
- Click Connect: initiates OAuth flow
- Shows: account name, connected date, token expiry
- Re-authorise button (token refresh)

### Brand Guidelines (/guidelines/:client_id)
- Colour pickers for brand colours
- Font selectors
- Tone keyword chips (add/remove)
- Forbidden words list (add/remove)
- Required elements toggles
- Logo upload (drag and drop to MinIO)
- Copy style notes (textarea)
- Save → updates brand_guidelines record

---

## 13. CODING STANDARDS

Same as sister systems:
- Type hints on all function signatures
- Docstrings on all classes and public methods
- All Claude calls through ai/claude.py only
- All platform API calls through platforms/*.py only
- All MinIO operations through media/storage.py only
- All ffmpeg operations through media/ffmpeg_ops.py only
- OAuth tokens always decrypted in memory, never logged
- Brand guidelines secrets (forbidden words, competitor names) never logged
- Celery tasks are thin wrappers — logic in agent classes
- Frontend API calls through src/api/ modules only

---

## 14. BUILD ORDER

### Phase 1 — Foundation
- [ ] Full folder structure
- [ ] requirements.txt + package.json
- [ ] .env.example
- [ ] docker-compose.yml (dev) — all 6 services start cleanly
- [ ] docker-compose.prod.yml
- [ ] Dockerfiles (ffmpeg included in api/worker image)
- [ ] MinIO bucket auto-created on startup
- [ ] db/models.py — all models
- [ ] Alembic migration runs inside Docker
- [ ] config.py with PLATFORM_SPECS constant
- [ ] README.md

### Phase 2 — AI + Context Layer
- [ ] ai/claude.py
- [ ] ai/dalle.py
- [ ] ai/elevenlabs_client.py
- [ ] ai/replicate_client.py
- [ ] ai/context_builder.py
- [ ] All prompt files stubbed
- [ ] media/storage.py (MinIO wrapper)
- [ ] media/ffmpeg_ops.py (ffmpeg wrapper)
- [ ] media/image_ops.py (Pillow wrapper)

### Phase 3 — Director + Planner
- [ ] agents/base.py
- [ ] agents/director.py
- [ ] agents/planner.py
- [ ] tasks/celery_app.py
- [ ] tasks/pipeline_tasks.py (stubs)
- [ ] Test: campaign created, calendar generated, gate created

### Phase 4 — Text Creation Agents
- [ ] agents/text/copywriter.py
- [ ] agents/text/seo_content.py
- [ ] agents/text/ad_copy.py
- [ ] Test: full text content generated for a 30-day campaign

### Phase 5 — Image Creation + Editing
- [ ] agents/image/generator.py (DALL-E 3)
- [ ] agents/image/sourcing.py (Unsplash + Pexels)
- [ ] agents/image/graphic_design.py (Canva or fallback)
- [ ] agents/editing/image_editor.py (Pillow)
- [ ] agents/editing/brand_consistency.py (images)
- [ ] Test: images generated, edited, brand-checked

### Phase 6 — Video Creation + Editing
- [ ] agents/video/script.py
- [ ] agents/video/voiceover.py
- [ ] agents/video/broll.py
- [ ] agents/video/assembly.py
- [ ] agents/editing/caption.py
- [ ] agents/editing/video_editor.py
- [ ] agents/editing/brand_consistency.py (video)
- [ ] Test: full 30-second video assembled with voiceover + subs + brand overlay

### Phase 7 — OAuth + Platform Connections
- [ ] platforms/base.py
- [ ] platforms/meta.py (Facebook + Instagram + WhatsApp)
- [ ] platforms/google.py (Google Business + YouTube)
- [ ] platforms/linkedin.py
- [ ] platforms/tiktok.py
- [ ] platforms/twitter.py
- [ ] api/routes/oauth.py (initiate + callback for all platforms)
- [ ] Test: OAuth flow works end-to-end for Meta (most complex)

### Phase 8 — Publishing Pipeline
- [ ] agents/publishing/formatter.py
- [ ] agents/publishing/scheduler.py
- [ ] agents/publishing/publisher.py
- [ ] tasks/scheduled_tasks.py (Celery Beat)
- [ ] Test: post scheduled, published at correct time via mock platform API

### Phase 9 — Analytics
- [ ] agents/publishing/analytics.py
- [ ] Celery Beat delayed tasks: 24h, 72h, 7d snapshots
- [ ] Test: analytics pulled for all platforms

### Phase 10 — Full API + Frontend GUI
- [ ] All FastAPI routes
- [ ] WebSocket live updates
- [ ] All frontend pages
- [ ] End-to-end: campaign created → content generated → approved → published → analytics

### Phase 11 — Documentation
- [ ] All docs/ files written
- [ ] docs/OAUTH_SETUP.md — step by step per platform

---

## 15. SESSION HANDOFF PROTOCOL

End of every session — update PROGRESS.md:

```markdown
## Last Updated
[ISO timestamp] by [model name]

## Current Phase
Phase X — [name]

## Completed This Session
- [x] item

## In Progress
- [ ] item

## Decisions Made
- [decision + reason]

## Blockers
- [unresolved]

## Files Modified
- path/file.py — what changed

## Next Session Starts With
[Exact instruction]
```

---

*MASTER_PROMPT.md — do not modify.*
*Only PROGRESS.md changes each session.*
