"""Celery Beat tasks — time-based publishing and analytics collection."""
import logging
from backend.tasks.celery_app import celery_app
from backend.db.session import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, queue="publishing", name="backend.tasks.scheduled_tasks.publish_post")
def publish_post(self, scheduled_post_id: int):
    from backend.agents.publishing.publisher import PublisherAgent
    db = SessionLocal()
    try:
        return PublisherAgent(db).run(scheduled_post_id)
    except Exception as exc:
        logger.exception("Publish failed for scheduled_post %d", scheduled_post_id)
        raise self.retry(exc=exc, countdown=300, max_retries=2)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2, queue="analytics", name="backend.tasks.scheduled_tasks.pull_analytics")
def pull_analytics(self, published_post_id: int, snapshot_type: str):
    from backend.agents.publishing.analytics import AnalyticsAgent
    db = SessionLocal()
    try:
        return AnalyticsAgent(db).run(published_post_id, snapshot_type)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=600)
    finally:
        db.close()
