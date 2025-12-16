#!/bin/sh
set -e

if [ "$SERVICE" = "web" ]; then
  echo "Starting FastAPI..."
  exec uvicorn app:app \
    --host 0.0.0.0 \
    --port 8000

elif [ "$SERVICE" = "worker" ]; then
  echo "Starting Celery worker..."
  exec celery -A main.celery_app.celery_app worker \
    --loglevel=info \
    --concurrency=${CELERY_CONCURRENCY:-2} \
    --prefetch-multiplier=1 \
    -P prefork

else
  echo "Unknown SERVICE: $SERVICE"
  exit 1
fi
