#!/usr/bin/env bash
# After: pip install -e ".[dev]"  and  docker compose up -d
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg2://cgd:cgd_dev_change_me@127.0.0.1:5432/cgd}"

echo "Starting Postgres + Redis (if not already)..."
docker compose up -d

echo "Waiting for Postgres..."
for _ in $(seq 1 60); do
  if docker compose exec -T postgres pg_isready -U cgd -d cgd >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
if ! docker compose exec -T postgres pg_isready -U cgd -d cgd >/dev/null 2>&1; then
  echo "Postgres did not become ready in time." >&2
  exit 1
fi

echo "Applying migrations..."
alembic upgrade head

echo "Seeding entities..."
python scripts/seed_entities.py

echo "Done. DB schema is ready. Start Celery worker + beat next."
