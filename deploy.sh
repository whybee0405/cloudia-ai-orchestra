#!/usr/bin/env bash
# CloudIA AI Orchestra — clean redeploy
# Usage: bash deploy.sh
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "ERROR: .env not found. Copy .env.example and fill in your secrets first."
  exit 1
fi

echo "==> Stopping and removing existing containers..."
docker compose down --remove-orphans

echo "==> Building images and starting all services..."
docker compose up -d --build

echo "==> Waiting for services to become healthy (up to 3 minutes)..."
sleep 10

for i in $(seq 1 17); do
  UNHEALTHY=$(docker compose ps --format json 2>/dev/null \
    | python3 -c "
import sys, json
lines = sys.stdin.read().strip().split('\n')
unhealthy = []
for line in lines:
    if not line: continue
    try:
        s = json.loads(line)
        name = s.get('Name','')
        health = s.get('Health','')
        status = s.get('State','')
        if status == 'running' and health == 'unhealthy':
            unhealthy.append(name)
    except: pass
print('\n'.join(unhealthy))
" 2>/dev/null || echo "")

  if [ -z "$UNHEALTHY" ]; then
    break
  fi
  echo "    Waiting... (unhealthy: $UNHEALTHY)"
  sleep 10
done

echo ""
echo "==> Service status:"
docker compose ps

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  https://agents.cloudia.co.za"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
