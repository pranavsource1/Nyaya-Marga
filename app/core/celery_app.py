"""Celery application configuration for async task processing."""
from celery import Celery
from .config import settings

celery_app = Celery(
    "nyaya_marga",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
)

# Import tasks to register them with Celery
celery_app.autodiscover_tasks(['app.worker'])
