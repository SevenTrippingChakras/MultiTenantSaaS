#!/usr/bin/env bash
# Start THIS project's own Redis on localhost:6379 for native dev + tests.
# Uses the `redis` service from docker-compose.yml (container: chatprod-redis).
# Redis runs as its own process next to the app; the app connects via REDIS_URI.
set -euo pipefail
cd "$(dirname "$0")/.."

# Only one process can hold port 6379. If another project's Redis is on it,
# stop that one first (this project brings up its own, same port).
if lsof -iTCP:6379 -sTCP:LISTEN -Pn >/dev/null 2>&1; then
  if [ "$(docker ps --filter name=chatprod-redis --filter status=running -q)" = "" ]; then
    echo "Port 6379 is already in use by something other than chatprod-redis."
    echo "Stop that process/container first, then re-run this script."
    lsof -iTCP:6379 -sTCP:LISTEN -Pn || true
    exit 1
  fi
fi

docker compose up -d redis
echo "Waiting for Redis to be healthy..."
until [ "$(docker inspect -f '{{.State.Health.Status}}' chatprod-redis 2>/dev/null)" = "healthy" ]; do
  sleep 1
done
echo "chatprod-redis is up and healthy on localhost:6379"
