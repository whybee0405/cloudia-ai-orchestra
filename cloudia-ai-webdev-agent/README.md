# CloudIA AI Web Development Agent

A multi-agent AI system that builds WordPress and Shopify websites for SME clients.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 24+
- [Docker Compose](https://docs.docker.com/compose/install/) v2.20+
- Git

## Quick Start

### 1. Clone the repository

```bash
git clone <repository-url>
cd cloudia-ai-webdev-agent
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in the required values:

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key (required) |
| `SECRET_KEY` | Random 32-character string for JWT signing |
| `ENCRYPTION_KEY` | Fernet key for encrypting platform credentials |
| `DB_PASSWORD` | PostgreSQL password |
| `UNSPLASH_ACCESS_KEY` | Unsplash API key for stock images (optional) |
| `PEXELS_API_KEY` | Pexels API key for stock images (optional) |
| `SMTP_*` | Email settings for client notifications (optional) |

Generate a `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Generate an `ENCRYPTION_KEY`:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. Start the development environment

```bash
docker compose -f docker/docker-compose.yml up --build
```

This starts five services:
- **db** — PostgreSQL 15 on port `5432`
- **redis** — Redis 7 on port `6379`
- **api** — FastAPI (uvicorn) on port `8000` with hot reload
- **worker** — Celery worker with concurrency 4
- **frontend** — Vite dev server on port `5173` with hot reload

### 4. Run database migrations

In a separate terminal (while the stack is running):

```bash
docker compose -f docker/docker-compose.yml exec api alembic upgrade head
```

### 5. Access the application

| Service | URL |
|---|---|
| Frontend (UI) | http://localhost:5173 |
| API (FastAPI) | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |

## Development Workflow

### Stopping the stack

```bash
docker compose -f docker/docker-compose.yml down
```

To also remove volumes (wipes the database):
```bash
docker compose -f docker/docker-compose.yml down -v
```

### Creating a new database migration

After modifying models in `backend/db/models.py`:

```bash
docker compose -f docker/docker-compose.yml exec api \
  alembic revision --autogenerate -m "describe your change here"
```

Then apply it:

```bash
docker compose -f docker/docker-compose.yml exec api alembic upgrade head
```

### Running tests

```bash
docker compose -f docker/docker-compose.yml exec api pytest tests/ -v
```

### Linting

```bash
docker compose -f docker/docker-compose.yml exec api ruff check backend/
```

## Production Deployment

Use the production compose file:

```bash
cp .env.example .env.prod
# Edit .env.prod with production values and ENVIRONMENT=production

docker compose -f docker/docker-compose.prod.yml up -d --build
```

SSL certificates are managed by Certbot. On first run, issue a certificate:

```bash
docker compose -f docker/docker-compose.prod.yml run --rm certbot \
  certonly --webroot --webroot-path=/var/www/certbot \
  -d yourdomain.com -d www.yourdomain.com \
  --email admin@yourdomain.com --agree-tos --no-eff-email
```

Then restart nginx:

```bash
docker compose -f docker/docker-compose.prod.yml restart nginx
```

## Architecture Overview

```
cloudia-ai-webdev-agent/
├── backend/
│   ├── agents/          # AI agent implementations
│   │   ├── shared/      # Shared agent utilities
│   │   ├── wordpress/   # WordPress-specific agents
│   │   └── shopify/     # Shopify-specific agents
│   ├── ai/              # Claude AI integration
│   │   └── prompts/     # System and user prompt templates
│   ├── api/             # FastAPI application and routes
│   │   └── routes/      # Route handlers
│   ├── db/              # Database layer
│   │   ├── models.py    # SQLAlchemy models
│   │   ├── session.py   # DB session management
│   │   └── migrations/  # Alembic migrations
│   ├── notifications/   # Email/webhook notifications
│   ├── platforms/       # Platform API clients
│   │   ├── wordpress/   # WordPress REST API client
│   │   └── shopify/     # Shopify API client
│   ├── tasks/           # Celery task definitions
│   ├── config.py        # Pydantic settings
│   ├── main.py          # ASGI entry point
│   └── worker.py        # Celery entry point
├── frontend/            # React/Vite frontend
│   └── src/
├── docker/              # Docker configuration
│   ├── Dockerfile.api
│   ├── Dockerfile.frontend
│   ├── nginx/
│   ├── docker-compose.yml
│   └── docker-compose.prod.yml
├── tests/               # Test suite
├── docs/                # Documentation
├── requirements.txt
├── alembic.ini
└── .env.example
```
