"""Celery application with Beat schedule."""
from celery import Celery
from backend.config import get_settings

settings = get_settings()

celery_app = Celery(
    "cloudia_content",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "backend.tasks.pipeline_tasks",
        "backend.tasks.scheduled_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone=settings.celery_timezone,
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "backend.tasks.pipeline_tasks.*": {"queue": "content"},
        "backend.tasks.scheduled_tasks.publish_post": {"queue": "publishing"},
        "backend.tasks.scheduled_tasks.pull_analytics": {"queue": "analytics"},
    },
)
