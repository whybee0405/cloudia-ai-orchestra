#!/usr/bin/env bash
# deploy.sh — Rebuild and redeploy the CloudIA Google Ads Agent containers.
#
# Usage:
#   ./deploy.sh           # Production deploy (default)
#   ./deploy.sh --dev     # Development deploy with hot-reload

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DEV=false
for arg in "$@"; do
  case $arg in
    --dev) DEV=true ;;
    *) echo "Unknown argument: $arg" && exit 1 ;;
  esac
done

if [ "$DEV" = true ]; then
  COMPOSE_FILE="docker-compose.dev.yml"
  SERVICE="ads-agent"
  echo "==> Deploying in DEVELOPMENT mode (hot-reload)"
else
  COMPOSE_FILE="docker-compose.yml"
  SERVICE="ads-agent"
  echo "==> Deploying in PRODUCTION mode (port 8020)"
fi

# Verify .env exists
if [ ! -f "google_ads_agents/.env" ]; then
  echo "ERROR: google_ads_agents/.env not found."
  echo "       Copy google_ads_agents/.env.example to google_ads_agents/.env and fill in all values."
  exit 1
fi

echo "==> Pulling latest changes..."
# Only pull if this is a git repo — safe to skip in other setups
if git rev-parse --is-inside-work-tree &>/dev/null 2>&1; then
  git pull
fi

echo "==> Stopping existing containers..."
docker compose -f "$COMPOSE_FILE" down --remove-orphans

echo "==> Rebuilding image (no cache)..."
docker compose -f "$COMPOSE_FILE" build --no-cache "$SERVICE"

echo "==> Ensuring database exists..."
if [ "$DEV" = true ]; then
  # Dev: wait for the local postgres container, then create DB if missing
  docker compose -f "$COMPOSE_FILE" up -d ads-agent-db
  sleep 3
  docker compose -f "$COMPOSE_FILE" exec ads-agent-db \
    psql -U adsagent -d postgres \
    -c "SELECT 1 FROM pg_database WHERE datname='google_ads_agents'" \
    | grep -q 1 \
    || docker compose -f "$COMPOSE_FILE" exec ads-agent-db \
         psql -U adsagent -d postgres -c "CREATE DATABASE google_ads_agents;"
else
  # Production: create DB inside the existing cloudia_postgres container if missing
  docker exec cloudia_postgres \
    psql -U cloudia -d postgres \
    -tc "SELECT 1 FROM pg_database WHERE datname='google_ads_agents'" \
    | grep -q 1 \
    || docker exec cloudia_postgres \
         psql -U cloudia -d postgres -c "CREATE DATABASE google_ads_agents;"
fi

echo "==> Running database migrations..."
if [ "$DEV" = true ]; then
  docker compose -f "$COMPOSE_FILE" run --rm ads-agent-migrate
else
  docker compose -f "$COMPOSE_FILE" run --rm ads-agent-db-init
fi

echo "==> Starting services..."
docker compose -f "$COMPOSE_FILE" up -d "$SERVICE"

echo "==> Waiting for health check..."
sleep 4
if curl -sf http://localhost:8020/health >/dev/null 2>&1; then
  echo "==> Done. System is up and healthy."
  echo "    Dashboard: http://localhost:8020/"
  echo "    API docs:  http://localhost:8020/docs"
  echo "    Health:    http://localhost:8020/health"
else
  echo "WARNING: Health check did not respond. Check logs with:"
  echo "  docker compose -f $COMPOSE_FILE logs $SERVICE"
fi
