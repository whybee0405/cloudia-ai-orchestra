"""
Celery task wrappers for all CloudIA pipeline agents.

Each task is a thin wrapper: it loads the agent, calls execute(), then
queues the next task if the pipeline should continue.
Approval gate checks happen inside tasks — if the gate is not approved,
the task retries with a 30-second countdown.
"""

import structlog
from celery import shared_task
from sqlalchemy import select

from backend.tasks.celery_app import celery_app
from backend.db.models import AgentTask, ApprovalGate, Project
from backend.db.session import get_db

log = structlog.get_logger()


def _get_next_pending_task(project_id: int, current_order: int) -> AgentTask | None:
    """Find the next pending task after the current pipeline_order."""
    with get_db() as db:
        return db.execute(
            select(AgentTask)
            .where(
                AgentTask.project_id == project_id,
                AgentTask.pipeline_order > current_order,
                AgentTask.status == "pending",
            )
            .order_by(AgentTask.pipeline_order)
            .limit(1)
        ).scalar_one_or_none()


def _check_gate(project_id: int, gate_name: str) -> bool:
    """Return True if the named gate is approved for this project."""
    with get_db() as db:
        gate = db.execute(
            select(ApprovalGate).where(
                ApprovalGate.project_id == project_id,
                ApprovalGate.gate_name == gate_name,
            )
        ).scalar_one_or_none()
        return gate is not None and gate.status == "approved"


def _queue_next(project_id: int, current_order: int) -> None:
    """Find and queue the next pending pipeline task."""
    next_task = _get_next_pending_task(project_id, current_order)
    if not next_task:
        log.info("pipeline_complete", project_id=project_id)
        return

    task_map = {
        "content_agent": run_content_agent,
        "media_agent": run_media_agent,
        "seo_agent": run_seo_agent,
        "wp_structure_agent": run_wp_structure_agent,
        "wp_builder_agent": run_wp_builder_agent,
        "wp_qa_agent": run_wp_qa_agent,
        "shopify_structure_agent": run_shopify_structure_agent,
        "shopify_builder_agent": run_shopify_builder_agent,
        "shopify_theme_agent": run_shopify_theme_agent,
        "shopify_qa_agent": run_shopify_qa_agent,
    }

    celery_task = task_map.get(next_task.agent_name)
    if celery_task:
        celery_task.delay(project_id=project_id, task_id=next_task.id)
        log.info("next_task_queued", agent=next_task.agent_name, task_id=next_task.id)
    else:
        log.error("unknown_agent_name", agent_name=next_task.agent_name)


@celery_app.task(bind=True, name="run_content_agent", max_retries=3)
def run_content_agent(self, project_id: int, task_id: int) -> dict:
    from backend.agents.shared.content_agent import ContentAgent
    try:
        agent = ContentAgent(project_id=project_id, task_id=task_id)
        result = agent.execute()
        # Content agent creates its own gate — do NOT auto-queue next task.
        # Next task (media_agent) is queued when the gate is approved via the API.
        return result
    except Exception as exc:
        log.error("content_agent_failed", project_id=project_id, error=str(exc))
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, name="run_media_agent", max_retries=3)
def run_media_agent(self, project_id: int, task_id: int) -> dict:
    if not _check_gate(project_id, "content_review"):
        raise self.retry(countdown=30, max_retries=240)  # wait up to 2 hours
    from backend.agents.shared.media_agent import MediaAgent
    try:
        agent = MediaAgent(project_id=project_id, task_id=task_id)
        result = agent.execute()
        # After media: load current task to get pipeline_order then queue next
        with get_db() as db:
            task = db.get(AgentTask, task_id)
            order = task.pipeline_order if task else 2
        _queue_next(project_id, order)
        return result
    except Exception as exc:
        log.error("media_agent_failed", project_id=project_id, error=str(exc))
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, name="run_seo_agent", max_retries=3)
def run_seo_agent(self, project_id: int, task_id: int) -> dict:
    from backend.agents.shared.seo_agent import SEOAgent
    try:
        agent = SEOAgent(project_id=project_id, task_id=task_id)
        result = agent.execute()
        with get_db() as db:
            task = db.get(AgentTask, task_id)
            order = task.pipeline_order if task else 5
        _queue_next(project_id, order)
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, name="run_wp_structure_agent", max_retries=3)
def run_wp_structure_agent(self, project_id: int, task_id: int) -> dict:
    from backend.agents.wordpress.structure_agent import WPStructureAgent
    try:
        agent = WPStructureAgent(project_id=project_id, task_id=task_id)
        result = agent.execute()
        with get_db() as db:
            task = db.get(AgentTask, task_id)
            order = task.pipeline_order if task else 3
        _queue_next(project_id, order)
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, name="run_wp_builder_agent", max_retries=3)
def run_wp_builder_agent(self, project_id: int, task_id: int) -> dict:
    from backend.agents.wordpress.builder_agent import WPBuilderAgent
    try:
        agent = WPBuilderAgent(project_id=project_id, task_id=task_id)
        result = agent.execute()
        with get_db() as db:
            task = db.get(AgentTask, task_id)
            order = task.pipeline_order if task else 4
        _queue_next(project_id, order)
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, name="run_wp_qa_agent", max_retries=2)
def run_wp_qa_agent(self, project_id: int, task_id: int) -> dict:
    from backend.agents.wordpress.qa_agent import WPQAAgent
    try:
        agent = WPQAAgent(project_id=project_id, task_id=task_id)
        return agent.execute()
        # QA agent creates site_review gate or marks project failed — no next task
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, name="run_shopify_structure_agent", max_retries=3)
def run_shopify_structure_agent(self, project_id: int, task_id: int) -> dict:
    from backend.agents.shopify.structure_agent import ShopifyStructureAgent
    try:
        agent = ShopifyStructureAgent(project_id=project_id, task_id=task_id)
        result = agent.execute()
        with get_db() as db:
            task = db.get(AgentTask, task_id)
            order = task.pipeline_order if task else 3
        _queue_next(project_id, order)
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, name="run_shopify_builder_agent", max_retries=3)
def run_shopify_builder_agent(self, project_id: int, task_id: int) -> dict:
    from backend.agents.shopify.builder_agent import ShopifyBuilderAgent
    try:
        agent = ShopifyBuilderAgent(project_id=project_id, task_id=task_id)
        result = agent.execute()
        with get_db() as db:
            task = db.get(AgentTask, task_id)
            order = task.pipeline_order if task else 4
        _queue_next(project_id, order)
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, name="run_shopify_theme_agent", max_retries=3)
def run_shopify_theme_agent(self, project_id: int, task_id: int) -> dict:
    from backend.agents.shopify.theme_agent import ShopifyThemeAgent
    try:
        agent = ShopifyThemeAgent(project_id=project_id, task_id=task_id)
        result = agent.execute()
        with get_db() as db:
            task = db.get(AgentTask, task_id)
            order = task.pipeline_order if task else 5
        _queue_next(project_id, order)
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, name="run_shopify_qa_agent", max_retries=2)
def run_shopify_qa_agent(self, project_id: int, task_id: int) -> dict:
    from backend.agents.shopify.qa_agent import ShopifyQAAgent
    try:
        agent = ShopifyQAAgent(project_id=project_id, task_id=task_id)
        return agent.execute()
        # QA creates store_review gate or marks project failed — no next task
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
