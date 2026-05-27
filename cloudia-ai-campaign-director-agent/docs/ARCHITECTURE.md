# CloudIA Content & Marketing Agent System — Architecture

## Overview

CloudIA is a multi-agent content pipeline that generates, reviews, formats, schedules, publishes, and analyses social media content for multiple clients from a single operator interface.

## System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI (port 8001)                       │
│  /campaigns  /calendar  /assets  /approvals  /publishing        │
│  /analytics  /settings  /oauth  /ws/{campaign_id}               │
└───────────────────────┬─────────────────────────────────────────┘
                        │ HTTP + WebSocket
┌───────────────────────▼─────────────────────────────────────────┐
│                    React Frontend (port 5174)                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────── AGENT PIPELINE ──────────────────────────────┐
│                                                                   │
│  Campaign Created → DirectorAgent                                 │
│       ↓                                                          │
│  PlannerAgent → [ApprovalGate: calendar_review]                  │
│       ↓ (approved)                                               │
│  Per calendar item:                                              │
│    CopywriterAgent ──────────────────────────────┐              │
│    ImageGeneratorAgent / VideoScriptAgent          │              │
│       ↓ (video only)                              │              │
│    [VoiceoverAgent + BRollAgent] (parallel)       │              │
│    VideoAssemblerAgent                            │              │
│    CaptionAgent + VideoEditorAgent (parallel)     │              │
│       ↓ (all asset types)                         │              │
│    ImageEditorAgent / GraphicDesignAgent          │              │
│    BrandConsistencyAgent ←──────────────────────-┘              │
│       ↓ (CRITICAL/HIGH fail → blocked)                          │
│  [ApprovalGate: content_batch_review]                            │
│       ↓ (approved)                                               │
│  FormatterAgent (per platform)                                   │
│  SchedulerAgent → Celery Beat ETA task                          │
│  PublisherAgent (fires at scheduled_for)                        │
│  AnalyticsAgent (24h / 72h / 7d delayed tasks)                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────── INFRASTRUCTURE ──────────────────────────────────┐
│  PostgreSQL 15 (port 5433)  — persistent state                  │
│  Redis 7 (port 6380)        — Celery broker + OAuth state       │
│  MinIO (port 9000/9001)     — media object storage              │
│  Celery Worker              — content, publishing, analytics     │
│  Celery Beat                — scheduled publish tasks           │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| API | FastAPI | 0.111 |
| ORM | SQLAlchemy | 2.0 |
| Migrations | Alembic | 1.13 |
| Task queue | Celery + Redis | 5.3 / 7 |
| Database | PostgreSQL | 15 |
| Object storage | MinIO | S3-compatible |
| AI text | Anthropic Claude | claude-sonnet-4-20250514 |
| AI images | OpenAI DALL-E 3 → Replicate Flux | fallback |
| AI voice | ElevenLabs | TTS |
| AI captions | OpenAI Whisper | transcription |
| Video | ffmpeg | system package |
| Image | Pillow | 10.3 |
| Frontend | React 18 + Vite 5 + Tailwind CSS 3 | |
| State management | React Query 5 | |
| Token encryption | Fernet (cryptography) | 42.0 |

## Service Ports

| Service | Dev Port | Reason for offset |
|---------|----------|-------------------|
| PostgreSQL | 5433 | avoid conflict with 5432 |
| Redis | 6380 | avoid conflict with 6379 |
| API | 8001 | avoid conflict with 8000 |
| Frontend | 5174 | avoid conflict with 5173 |
| MinIO API | 9000 | standard |
| MinIO Console | 9001 | standard |

## Multi-Client Architecture

Each client is fully isolated at:
- **Database level**: every row has a `client_id` FK
- **Storage level**: MinIO paths prefixed with `{client_id}/`
- **OAuth level**: tokens stored per-client, encrypted at rest
- **Publish level**: runtime check `account.client_id == campaign.client_id` raises `SecurityError` on mismatch
- **Signed URLs**: `client_id_prefix` validated before generating presigned URLs

## Agent Task Lifecycle

Every agent writes an `AgentTask` row:
```
pending → running → completed
                 ↘ failed
```

`pipeline_order` integers allow the frontend to show a progress bar.

## Approval Gates

Two hard stops require operator action before the pipeline continues:
1. `calendar_review` — after Planner, before any content generation
2. `content_batch_review` — after Brand Consistency, before Formatter/Scheduler

Gates are rows in `approval_gates`. The API exposes `POST /approvals/{id}/approve` and `POST /approvals/{id}/reject`.

## Celery Queues

| Queue | Workers | Used by |
|-------|---------|---------|
| `content` | worker | all content generation agents |
| `publishing` | worker | Formatter, Scheduler, Publisher |
| `analytics` | worker | AnalyticsAgent |

## Security Model

- ENCRYPTION_KEY env var required at startup (app refuses to start without it)
- All platform tokens encrypted with Fernet before DB write
- OAuth state tokens: 32-byte cryptographically random, Redis TTL 600s, consumed once
- Prompt injection: all client-provided strings wrapped in `[DATA_START]...[DATA_END]`
- Cross-client isolation enforced at publish time with `SecurityError`
