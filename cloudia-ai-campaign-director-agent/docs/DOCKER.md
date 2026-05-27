# Docker Setup

## Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| db | postgres:15-alpine | 5433:5432 | PostgreSQL database |
| redis | redis:7-alpine | 6380:6379 | Celery broker + OAuth state |
| minio | minio/minio | 9000, 9001 | Object storage (S3-compatible) |
| api | ./docker/Dockerfile.api | 8001:8000 | FastAPI application |
| worker | ./docker/Dockerfile.api | — | Celery worker (content, publishing, analytics) |
| beat | ./docker/Dockerfile.api | — | Celery Beat scheduler |
| frontend | ./docker/Dockerfile.frontend | 5174:5173 | React dev server |

## Prerequisites

- Docker Desktop 4.x+ or Docker Engine 24+ with Compose plugin
- Minimum 4 GB RAM (dev), 8 GB RAM (prod)
- ffmpeg is installed at image build time — not required on host

## Quick Start (Development)

```bash
# 1. Copy environment file
cp .env.example .env
# Edit .env — set ENCRYPTION_KEY, API keys, etc.

# 2. Start all services
docker compose up

# 3. Run migrations (first time only)
docker compose exec api alembic upgrade head

# 4. Access
#   API: http://localhost:8001
#   Frontend: http://localhost:5174
#   MinIO console: http://localhost:9001  (minioadmin / minioadmin123)
#   API docs: http://localhost:8001/docs
```

## Environment Variables

Copy from `.env.example`. Required values with no default:

| Variable | Description |
|----------|-------------|
| `ENCRYPTION_KEY` | Fernet key for token encryption — **app refuses to start without this** |
| `ANTHROPIC_API_KEY` | Claude API key |
| `OPENAI_API_KEY` | DALL-E 3 + Whisper |
| `DATABASE_URL` | Set by docker-compose; override for external DB |
| `REDIS_URL` | Set by docker-compose; override for external Redis |

Optional but needed for full functionality:

| Variable | Default | Description |
|----------|---------|-------------|
| `REPLICATE_API_TOKEN` | — | Flux fallback for image generation |
| `ELEVENLABS_API_KEY` | — | TTS voiceover |
| `META_APP_ID` | — | Instagram + Facebook OAuth |
| `META_APP_SECRET` | — | |
| `GOOGLE_CLIENT_ID` | — | YouTube + Google Business OAuth |
| `GOOGLE_CLIENT_SECRET` | — | |
| `LINKEDIN_CLIENT_ID` | — | LinkedIn OAuth |
| `LINKEDIN_CLIENT_SECRET` | — | |
| `TIKTOK_CLIENT_KEY` | — | TikTok OAuth |
| `TIKTOK_CLIENT_SECRET` | — | |
| `TWITTER_CLIENT_ID` | — | Twitter OAuth |
| `TWITTER_CLIENT_SECRET` | — | |
| `UNSPLASH_ACCESS_KEY` | — | Stock images |
| `PEXELS_API_KEY` | — | Stock photos + videos |
| `CANVA_API_KEY` | — | Graphic design (optional, has fallback) |
| `OAUTH_CALLBACK_BASE_URL` | http://localhost:8001 | Base URL for OAuth redirect URIs |
| `MINIO_BUCKET` | cloudia-media | Object storage bucket name |
| `SECRET_KEY` | — | API authentication header value |

## Hot Reload

In dev mode:
- API container mounts `./backend` as a volume; Uvicorn auto-reloads on Python file changes
- Frontend container mounts `./frontend/src`; Vite HMR handles React changes

## Production Build

```bash
docker compose -f docker/docker-compose.prod.yml up --build
```

Differences from dev:
- API: `uvicorn --workers 4` (no reload)
- Frontend: built to static files, served by Nginx
- MinIO not exposed externally (no host ports)
- PostgreSQL volume backed by named Docker volume for persistence

## Verify Installation

```bash
# ffmpeg in API container
docker compose exec api ffmpeg -version

# ffmpeg in worker container
docker compose exec worker ffmpeg -version

# Pillow
docker compose exec api python -c "from PIL import Image; print('Pillow OK')"

# Celery worker status
docker compose exec worker celery -A backend.worker inspect active

# MinIO bucket
docker compose exec api python -c "from backend.media.storage import ensure_bucket; ensure_bucket(); print('Bucket OK')"
```

## Port Conflict Check

Sister systems may use default ports. This system uses:
- 5433 (not 5432) for PostgreSQL
- 6380 (not 6379) for Redis
- 8001 (not 8000) for API
- 5174 (not 5173) for Frontend

If conflicts occur, change the host-side port in `docker/docker-compose.yml` (left side of `ports:` mapping).

## Database Migrations

```bash
# Apply all pending migrations
docker compose exec api alembic upgrade head

# Create a new migration after changing models.py
docker compose exec api alembic revision --autogenerate -m "description"

# Rollback one migration
docker compose exec api alembic downgrade -1
```

## Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f worker
docker compose logs -f api

# Filter for errors
docker compose logs api 2>&1 | grep ERROR
```
