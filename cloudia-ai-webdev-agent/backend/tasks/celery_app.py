"""Celery application configuration for CloudIA agent task queue."""

from celery import Celery
from backend.config import settings

celery_app = Celery(
    "cloudia_agents",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["backend.tasks.pipeline_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Johannesburg",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=600,   # 10 min soft limit per task
    task_time_limit=900,        # 15 min hard limit
    broker_connection_retry_on_startup=True,
)
