#!/bin/sh
# entrypoint.sh — production startup script
# 1. Waits for PostgreSQL to accept connections (via pg_isready in healthcheck),
#    but also re-checks here so `alembic upgrade head` never races with postgres.
# 2. Runs Alembic migrations (idempotent — safe to run on every boot).
# 3. Starts uvicorn.

set -e

echo "[entrypoint] Waiting for PostgreSQL to be ready..."
until pg_isready -h "${PGHOST:-postgres}" -U "${PGUSER:-raguser}" -d "${PGDATABASE:-ragdb}" -q; do
  echo "[entrypoint] PostgreSQL not ready yet, sleeping 2s..."
  sleep 2
done
echo "[entrypoint] PostgreSQL is ready."

echo "[entrypoint] Running Alembic migrations..."
alembic upgrade head
echo "[entrypoint] Migrations applied."

echo "[entrypoint] Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
