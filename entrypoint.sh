#!/usr/bin/env sh
set -e

echo "[entrypoint] Running database migrations via Alembic..."
alembic upgrade head

echo "[entrypoint] Starting application process: $@"
# 'exec' replaces the shell process so the CMD (Uvicorn) becomes PID 1,
# allowing it to directly receive SIGTERM and SIGINT from Docker.
exec "$@"