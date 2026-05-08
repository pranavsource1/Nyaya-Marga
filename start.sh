#!/bin/bash

# Start Redis server in the background with persistence disabled
# On Hugging Face Spaces, we don't need RDB snapshots and they often fail due to disk/permission limits.
redis-server --daemonize yes --save "" --appendonly no --stop-writes-on-bgsave-error no

# Wait a moment for Redis to start
sleep 2

# Start Celery worker in the background
celery -A app.core.celery_app worker --loglevel=info &

# Start the FastAPI application
uvicorn app.main:app --host 0.0.0.0 --port 7860
