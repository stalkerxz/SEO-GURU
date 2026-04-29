#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  echo "❌ .env not found. Run: cp .env.example .env"
  exit 1
fi

required_vars=(
  DATABASE_URL
  REDIS_URL
  MINIO_ENDPOINT
  MINIO_PORT
  MINIO_ACCESS_KEY
  MINIO_SECRET_KEY
  MINIO_BUCKET
  NEXT_PUBLIC_API_URL
)

for var in "${required_vars[@]}"; do
  if ! grep -qE "^${var}=" .env; then
    echo "❌ Missing env var in .env: ${var}"
    exit 1
  fi
done

echo "✅ .env contains required variables"

echo "🔎 docker compose ps"
docker compose ps

echo "🔎 API health"
curl -fsS http://localhost:4000/health > /dev/null

echo "🔎 Web availability"
curl -fsS http://localhost:3000 > /dev/null

echo "✅ Smoke check passed"
