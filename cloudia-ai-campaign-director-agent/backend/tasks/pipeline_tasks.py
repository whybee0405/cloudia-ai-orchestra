"""Celery tasks — thin wrappers around agent classes."""
import logging
from backend.tasks.celery_app import celery_app
from backend.db.session import SessionLocal

logger = logging.getLogger(__name__)


def _db():
    return SessionLocal()


@celery_app.task(bind=True, max_retries=3, queue="content", name="backend.tasks.pipeline_tasks.run_director")
def run_director(self, campaign_id: int):
    from backend.agents.director import DirectorAgent
    db = _db()
    try:
        result = DirectorAgent(db).run(campaign_id)
        run_planner.delay(campaign_id)
        return result
    except Exception as exc:
        logger.exception("Director failed for campaign %d", campaign_id)
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, queue="content", name="backend.tasks.pipeline_tasks.run_planner")
def run_planner(self, campaign_id: int):
    from backend.agents.planner import PlannerAgent
    db = _db()
    try:
        return PlannerAgent(db).run(campaign_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, queue="content", name="backend.tasks.pipeline_tasks.run_copywriter")
def run_copywriter(self, calendar_id: int):
    from backend.agents.text.copywriter import CopywriterAgent
    db = _db()
    try:
        return CopywriterAgent(db).run(calendar_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, queue="content", name="backend.tasks.pipeline_tasks.run_seo_content")
def run_seo_content(self, calendar_id: int):
    from backend.agents.text.seo_content import SEOContentAgent
    db = _db()
    try:
        return SEOContentAgent(db).run(calendar_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, queue="content", name="backend.tasks.pipeline_tasks.run_ad_copy")
def run_ad_copy(self, calendar_id: int):
    from backend.agents.text.ad_copy import AdCopyAgent
    db = _db()
    try:
        return AdCopyAgent(db).run(calendar_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, queue="content", name="backend.tasks.pipeline_tasks.run_image_generator")
def run_image_generator(self, calendar_id: int):
    from backend.agents.image.generator import ImageGeneratorAgent
    db = _db()
    try:
        return ImageGeneratorAgent(db).run(calendar_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, queue="content", name="backend.tasks.pipeline_tasks.run_image_sourcing")
def run_image_sourcing(self, calendar_id: int):
    from backend.agents.image.sourcing import ImageSourcingAgent
    db = _db()
    try:
        return ImageSourcingAgent(db).run(calendar_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, queue="content", name="backend.tasks.pipeline_tasks.run_image_editor")
def run_image_editor(self, asset_id: int):
    from backend.agents.editing.image_editor import ImageEditorAgent
    db = _db()
    try:
        return ImageEditorAgent(db).run(asset_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, queue="content", name="backend.tasks.pipeline_tasks.run_brand_consistency")
def run_brand_consistency(self, asset_id: int):
    from backend.agents.editing.brand_consistency import BrandConsistencyAgent
    db = _db()
    try:
        return BrandConsistencyAgent(db).run(asset_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, queue="content", name="backend.tasks.pipeline_tasks.run_video_script")
def run_video_script(self, calendar_id: int):
    from backend.agents.video.script import ScriptAgent
    db = _db()
    try:
        result = ScriptAgent(db).run(calendar_id)
        run_voiceover.delay(result["asset_id"])
        run_broll.delay(result["asset_id"])
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, queue="content", name="backend.tasks.pipeline_tasks.run_voiceover")
def run_voiceover(self, script_asset_id: int):
    from backend.agents.video.voiceover import VoiceoverAgent
    db = _db()
    try:
        return VoiceoverAgent(db).run(script_asset_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, queue="content", name="backend.tasks.pipeline_tasks.run_broll")
def run_broll(self, script_asset_id: int):
    from backend.agents.video.broll import BRollAgent
    db = _db()
    try:
        return BRollAgent(db).run(script_asset_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, queue="content", name="backend.tasks.pipeline_tasks.run_video_assembly")
def run_video_assembly(self, script_asset_id: int):
    from backend.agents.video.assembly import VideoAssemblyAgent
    db = _db()
    try:
        return VideoAssemblyAgent(db).run(script_asset_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=180)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, queue="content", name="backend.tasks.pipeline_tasks.run_formatter")
def run_formatter(self, asset_id: int):
    from backend.agents.publishing.formatter import FormatterAgent
    db = _db()
    try:
        return FormatterAgent(db).run(asset_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()
