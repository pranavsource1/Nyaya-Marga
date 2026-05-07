"""Worker process for Celery tasks.

Start with: celery -A app.core.celery_app worker --loglevel=info
"""
from app.core.celery_app import celery_app
from app.worker import tasks  # noqa: F401 - Import to register tasks

if __name__ == "__main__":
    celery_app.start()
