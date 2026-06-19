#!/bin/sh
set -e

echo "Running database migrations..."
cd /app
alembic upgrade head

WORKERS="${WORKERS:-2}"
echo "Starting FastAPI server with $WORKERS workers..."
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers "$WORKERS" \
  --access-log \
  --log-level info
