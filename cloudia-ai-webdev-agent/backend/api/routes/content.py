"""
Generated content routes for the CloudIA API.

Operators use these endpoints to review, edit, approve, and regenerate
AI-written page content before it is pushed to WordPress or Shopify.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.schemas import ContentOut, ContentUpdate
from backend.db.models import (
    AgentTask,
    AgentTaskStatus,
    ApprovalGate,
    ApprovalGateStatus,
    ContentStatus,
    GeneratedContent,
    Project,
    ProjectStatus,
)
from backend.db.session import get_session

log = structlog.get_logger()

router = APIRouter()


# ---------------------------------------------------------------------------
# Helper — ORM → schema
# ---------------------------------------------------------------------------


def _content_to_out(content: GeneratedContent) -> ContentOut:
    return ContentOut(
        id=content.id,
        page_slug=content.page_slug or "",
        content_type=content.content_type or "page",
        title=content.title,
        h1=content.h1,
        body_content=content.body_content,
        cta_text=content.cta_text,
        meta_title=content.meta_title,
        meta_description=content.meta_description,
        status=content.status,
        revision_notes=content.revision_notes,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/project/{project_id}", response_model=list[ContentOut])
def get_project_content(
    project_id: int,
    db: Session = Depends(get_session),
) -> list[ContentOut]:
    """Return all generated content pieces for a project."""
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    items = db.scalars(
        select(GeneratedContent)
        .where(GeneratedContent.project_id == project_id)
        .order_by(GeneratedContent.id)
    ).all()

    return [_content_to_out(item) for item in items]


@router.patch("/{content_id}", response_model=ContentOut)
def update_content(
    content_id: int,
    data: ContentUpdate,
    db: Session = Depends(get_session),
) -> ContentOut:
    """Update a content piece. Resets content_review gate to pending if previously approved."""
    content = db.get(GeneratedContent, content_id)
    if content is None:
        raise HTTPException(status_code=404, detail=f"Content {content_id} not found")

    update_dict = data.model_dump(exclude_none=True)
    for field, value in update_dict.items():
        setattr(content, field, value)

    content_gates = db.scalars(
        select(ApprovalGate).where(
            ApprovalGate.project_id == content.project_id,
            ApprovalGate.gate_name == "content_review",
            ApprovalGate.status == ApprovalGateStatus.APPROVED,
        )
    ).all()
    for gate in content_gates:
        gate.status = ApprovalGateStatus.PENDING
        gate.reviewed_at = None
        gate.reviewed_by = None
        log.info(
            "content_review_gate_reset",
            gate_id=gate.id,
            content_id=content_id,
            reason="content_updated",
        )

    db.commit()
    db.refresh(content)

    log.info(
        "content_updated",
        content_id=content_id,
        fields=list(update_dict.keys()),
    )
    return _content_to_out(content)


@router.post("/{content_id}/approve", response_model=ContentOut)
def approve_content_piece(
    content_id: int,
    db: Session = Depends(get_session),
) -> ContentOut:
    """Mark an individual content piece as approved."""
    content = db.get(GeneratedContent, content_id)
    if content is None:
        raise HTTPException(status_code=404, detail=f"Content {content_id} not found")

    content.status = ContentStatus.APPROVED
    db.commit()
    db.refresh(content)

    log.info("content_piece_approved", content_id=content_id)
    return _content_to_out(content)


@router.post("/project/{project_id}/approve-all")
def bulk_approve_content(
    project_id: int,
    db: Session = Depends(get_session),
) -> dict:
    """Approve all draft content pieces for a project."""
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    if project.status == ProjectStatus.CANCELLED:
        raise HTTPException(
            status_code=400,
            detail="Cannot approve content on a cancelled project",
        )

    items = db.scalars(
        select(GeneratedContent).where(
            GeneratedContent.project_id == project_id,
            GeneratedContent.status != ContentStatus.APPROVED,
        )
    ).all()

    count = 0
    for item in items:
        item.status = ContentStatus.APPROVED
        count += 1

    db.commit()

    log.info("content_bulk_approved", project_id=project_id, count=count)
    return {
        "detail": f"Approved {count} content piece(s)",
        "project_id": project_id,
        "approved_count": count,
    }


@router.post("/{content_id}/regenerate")
def regenerate_content(
    content_id: int,
    db: Session = Depends(get_session),
) -> dict:
    """Re-run the content agent for a single page only."""
    content = db.get(GeneratedContent, content_id)
    if content is None:
        raise HTTPException(status_code=404, detail=f"Content {content_id} not found")

    project = db.get(Project, content.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Associated project not found")

    if project.status == ProjectStatus.CANCELLED:
        raise HTTPException(
            status_code=400,
            detail="Cannot regenerate content on a cancelled project",
        )

    content.status = ContentStatus.DRAFT

    content_gates = db.scalars(
        select(ApprovalGate).where(
            ApprovalGate.project_id == project.id,
            ApprovalGate.gate_name == "content_review",
        )
    ).all()
    for gate in content_gates:
        gate.status = ApprovalGateStatus.PENDING
        gate.reviewed_at = None
        gate.reviewed_by = None

    project.status = ProjectStatus.RUNNING
    db.commit()

    existing_tasks = db.scalars(
        select(AgentTask).where(
            AgentTask.project_id == project.id,
            AgentTask.agent_name.contains("content"),
        )
    ).all()

    if existing_tasks:
        task = existing_tasks[-1]
        task.status = AgentTaskStatus.PENDING
        task.retry_count += 1
        task.error = None
        task.started_at = None
        task.completed_at = None
        input_data = task.input_data or {}
        input_data["regenerate_content_id"] = content_id
        input_data["page_slug"] = content.page_slug
        task.input_data = input_data
        db.commit()

        try:
            from backend.tasks.pipeline_tasks import run_content_agent  # noqa: PLC0415

            celery_result = run_content_agent.delay(
                project_id=project.id,
                task_id=task.id,
            )
            task.celery_task_id = celery_result.id
            db.commit()
            log.info(
                "content_regeneration_queued",
                content_id=content_id,
                task_id=task.id,
                project_id=project.id,
            )
        except Exception as exc:
            log.error(
                "content_regeneration_queue_failed",
                content_id=content_id,
                error=str(exc),
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to queue regeneration task: {exc}",
            ) from exc

        return {
            "detail": "Content regeneration queued",
            "content_id": content_id,
            "project_id": project.id,
            "task_id": task.id,
        }

    raise HTTPException(
        status_code=400,
        detail="No content agent task found for this project. "
               "Start the pipeline first via the Director agent.",
    )
