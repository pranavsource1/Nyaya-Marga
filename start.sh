#!/bin/bash

# Start Redis server in the background
redis-server --daemonize yes

# Wait a moment for Redis to start
sleep 2

# Start Celery worker in the background
celery -A app.core.celery_app worker --loglevel=info &

# Start the FastAPI application
uvicorn app.main:app --host 0.0.0.0 --port 7860
