# Docker Setup

## Development

### Services

| Service | Image | Port | Purpose |
|---|---|---|---|
| db | postgres:15-alpine | 5432 | PostgreSQL database |
| redis | redis:7-alpine | 6379 | Celery broker + result backend |
| api | Dockerfile.api | 8000 | FastAPI + uvicorn (hot reload) |
| worker | Dockerfile.api | — | Celery worker |
| frontend | Dockerfile.frontend | 5173 | Vite dev server (hot reload) |

### Starting Dev

```bash
cp .env.example .env
# Fill in ANTHROPIC_API_KEY at minimum
# Generate ENCRYPTION_KEY:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Add to .env

docker compose up --build
```

First run only — run database migrations:
```bash
docker compose exec api alembic upgrade head
```

### Hot Reload

- Backend: edit any file in `backend/` → uvicorn auto-reloads (volume mounted)
- Frontend: edit any file in `frontend/src/` → Vite HMR updates browser instantly

### Useful Commands

```bash
# View all logs
docker compose logs -f

# View specific service
docker compose logs -f worker

# Run migrations
docker compose exec api alembic upgrade head

# Create new migration
docker compose exec api alembic revision --autogenerate -m "add_column_x"

# Open DB shell
docker compose exec db psql -U cloudia -d cloudia_websites

# Run tests
docker compose exec api pytest tests/ -v --tb=short

# Restart single service
docker compose restart worker

# Stop all
docker compose down

# Stop + remove volumes (WARNING: deletes DB data)
docker compose down -v
```

## Production

### Pre-requisites
1. VPS with Docker + Docker Compose installed
2. Domain pointed at server IP
3. `.env.prod` created from `.env.example` with production values

### Deploy

```bash
# On VPS:
git clone <repo> cloudia-agents
cd cloudia-agents

cp .env.example .env.prod
# Edit .env.prod — set all values, ENVIRONMENT=production

# Build and start
docker compose -f docker/docker-compose.prod.yml up --build -d

# Run migrations
docker compose -f docker/docker-compose.prod.yml exec api alembic upgrade head

# Initial SSL cert (first time)
docker compose -f docker/docker-compose.prod.yml run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d yourdomain.co.za \
  --email admin@yourdomain.co.za \
  --agree-tos --no-eff-email
```

### SSL Renewal

Add to crontab on VPS:
```
0 12 * * * docker compose -f /path/to/docker-compose.prod.yml run --rm certbot renew --quiet && docker compose -f /path/to/docker-compose.prod.yml exec nginx nginx -s reload
```

### Memory Requirements

Minimum VPS for all services:
| Service | RAM estimate |
|---|---|
| PostgreSQL | 256 MB |
| Redis | 64 MB |
| FastAPI (2 workers) | 256 MB |
| Celery (4 workers) | 512 MB |
| Frontend (nginx) | 32 MB |
| **Total** | **~1.1 GB** |

Recommend minimum 2 GB VPS (R500/month on most ZA providers).

### Scaling

To increase Celery concurrency (more parallel agent tasks):
```yaml
# In docker-compose.prod.yml worker service:
command: celery -A backend.tasks.celery_app worker --loglevel=warning --concurrency=8
```

Each additional 4 workers adds ~512 MB RAM requirement.
