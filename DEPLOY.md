# CloudIA AI Orchestra — Deployment Runbook

## Prerequisites

- Docker 24+ and Docker Compose v2 on the host
- `git clone` the full monorepo
- A domain name pointed at the server's public IP (for SSL)

---

## First-time setup

### 1. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in every value. Key secrets to generate:

```bash
# INTERNAL_API_SECRET — shared by all services
openssl rand -hex 32

# CAMPAIGNS_SECRET_KEY
openssl rand -hex 32

# CAMPAIGNS_ENCRYPTION_KEY (Fernet format)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# ADS_SECRET_KEY
openssl rand -hex 32

# WEBDEV_SECRET_KEY
openssl rand -hex 32

# Database passwords (one per service)
openssl rand -hex 16
```

### 2. First launch (development / local)

```bash
docker compose up -d
```

This runs all services including database migrations via init containers. Wait ~30 seconds for all health checks to pass, then open:

- **Frontend**: http://localhost
- **Brand DNA API docs**: http://localhost/api/brand/docs (development environment only)
- **MinIO console**: http://localhost:9001 (campaigns media storage)

### 3. Verify everything is running

```bash
docker compose ps
docker compose logs --tail=20 brand-dna
docker compose logs --tail=20 campaigns-api
docker compose logs --tail=20 ads
docker compose logs --tail=20 webdev-api
```

---

## Production deployment (with SSL)

### 1. Point DNS at the server

Create an A record: `your-domain.com → <server IP>`

### 2. Issue SSL certificate

```bash
# Start nginx on port 80 first (HTTP only)
docker compose up -d nginx

# Issue certificate (replace with your domain and email)
docker run --rm \
  -v cloudia-ai-orchestra_certbot-webroot:/var/www/certbot \
  -v cloudia-ai-orchestra_certbot-certs:/etc/letsencrypt \
  certbot/certbot certonly \
  --webroot -w /var/www/certbot \
  -d your-domain.com \
  --email admin@your-domain.com \
  --agree-tos --non-interactive
```

### 3. Add SSL nginx config

Create `nginx/ssl.conf.template` to add the HTTPS server block and redirect HTTP → HTTPS. Then restart nginx:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d nginx
```

### 4. Start all services with prod overrides

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Routine operations

### View logs

```bash
# All services
docker compose logs -f

# Single service
docker compose logs -f campaigns-worker
```

### Database migrations (after code updates)

Migrations run automatically via init containers on every `docker compose up`. To run manually:

```bash
docker compose run --rm brand-dna-migrate
docker compose run --rm campaigns-migrate
docker compose run --rm ads-migrate
docker compose run --rm webdev-migrate
```

### Updating to a new release

```bash
git pull
docker compose pull   # pull any updated base images
docker compose up -d --build
```

This rebuilds all service images and restarts containers in dependency order. Migrations run automatically before each service starts.

### Restart a single service

```bash
docker compose restart campaigns-api
```

### Scale Celery workers

```bash
docker compose up -d --scale campaigns-worker=3 --scale webdev-worker=2
```

---

## Backup

### Database backups

```bash
# Brand DNA
docker compose exec postgres-brand pg_dump -U cloudia cloudia_brand_dna | gzip > backup-brand-$(date +%Y%m%d).sql.gz

# Campaigns
docker compose exec postgres-campaigns pg_dump -U cloudia cloudia_campaigns | gzip > backup-campaigns-$(date +%Y%m%d).sql.gz

# Ads
docker compose exec postgres-ads pg_dump -U cloudia cloudia_ads | gzip > backup-ads-$(date +%Y%m%d).sql.gz

# WebDev
docker compose exec postgres-webdev pg_dump -U cloudia cloudia_webdev | gzip > backup-webdev-$(date +%Y%m%d).sql.gz
```

### Restore from backup

```bash
gunzip -c backup-brand-20260101.sql.gz | docker compose exec -T postgres-brand psql -U cloudia cloudia_brand_dna
```

---

## Environment variable reference

| Variable | Used by | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Brand DNA, Campaigns, WebDev | Claude API key |
| `ANTHROPIC_MODEL` | Brand DNA, Campaigns, WebDev | Claude model ID (default: claude-sonnet-4-6) |
| `INTERNAL_API_SECRET` | All services | Shared secret for cross-service internal calls |
| `POSTGRES_BRAND_PASSWORD` | Brand DNA + postgres | DB password |
| `POSTGRES_CAMPAIGNS_PASSWORD` | Campaigns + postgres | DB password |
| `POSTGRES_ADS_PASSWORD` | Ads + postgres | DB password |
| `POSTGRES_WEBDEV_PASSWORD` | WebDev + postgres | DB password |
| `MINIO_ROOT_USER` | MinIO + Campaigns | MinIO admin username |
| `MINIO_ROOT_PASSWORD` | MinIO + Campaigns | MinIO admin password |
| `CAMPAIGNS_SECRET_KEY` | Campaign Director | JWT/session signing key |
| `CAMPAIGNS_ENCRYPTION_KEY` | Campaign Director | Fernet key for OAuth token encryption |
| `OAUTH_CALLBACK_BASE_URL` | Campaign Director | Base URL for OAuth redirect URIs |
| `ADS_SECRET_KEY` | Google Ads | API authentication key |
| `WEBDEV_SECRET_KEY` | WebDev + nginx | API authentication key injected by nginx |
| `META_APP_ID / META_APP_SECRET` | Campaign Director | Facebook/Instagram OAuth |
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Google Ads | Google Ads API token |

---

## Removing old standalone frontends

The three existing backend repos each had their own frontend. Once the unified frontend is deployed, you can remove them:

```bash
# Campaign Director
rm -rf cloudia-ai-campaign-director-agent/frontend

# Google Ads
rm -rf cloudia-ai-googleads-agent/google_ads_agents/frontend

# WebDev
rm -rf cloudia-ai-webdev-agent/frontend
```

---

## Service ports (internal network only)

| Service | Internal host | Port |
|---------|---------------|------|
| Brand DNA | `brand-dna` | 8000 |
| Campaign Director | `campaigns-api` | 8000 |
| Google Ads | `ads` | 8000 |
| WebDev | `webdev-api` | 8000 |
| Frontend | `frontend` | 80 |
| PostgreSQL (Brand DNA) | `postgres-brand` | 5432 |
| PostgreSQL (Campaigns) | `postgres-campaigns` | 5432 |
| PostgreSQL (Ads) | `postgres-ads` | 5432 |
| PostgreSQL (WebDev) | `postgres-webdev` | 5432 |
| Redis | `redis` | 6379 |
| MinIO API | `minio` | 9000 |
| MinIO Console | `minio` | 9001 |

Only nginx is exposed to the host (ports 80 and 443 in production).
