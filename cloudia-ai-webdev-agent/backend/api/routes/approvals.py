"""
Approval gate routes for the CloudIA API.

Operators use these endpoints to review and approve/reject pipeline checkpoints
before the next stage proceeds (e.g. content review before site build).
"""

from __future__ import annotations

from datetime import datetime, UTC

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.schemas import ApprovalAction, ApprovalGateOut, ApprovalReject
from backend.db.models import (
    AgentTask,
    AgentTaskStatus,
    ApprovalGate,
    ApprovalGateStatus,
    Project,
    ProjectStatus,
)
from backend.db.session import get_session

log = structlog.get_logger()

router = APIRouter()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _gate_to_out(gate: ApprovalGate) -> ApprovalGateOut:
    return ApprovalGateOut(
        id=gate.id,
        gate_name=gate.gate_name,
        pipeline_order=gate.pipeline_order,
        status=gate.status,
        notes=gate.notes,
        created_at=gate.created_at,
        reviewed_at=gate.reviewed_at,
        reviewed_by=gate.reviewed_by,
    )


def _get_gate_or_404(gate_id: int, db: Session) -> ApprovalGate:
    gate = db.get(ApprovalGate, gate_id)
    if gate is None:
        raise HTTPException(status_code=404, detail=f"Approval gate {gate_id} not found")
    return gate


def _assert_project_not_cancelled(gate: ApprovalGate, db: Session) -> Project:
    project = db.get(Project, gate.project_id)
    if project is None:
        raise HTTPException(
            status_code=404,
            detail=f"Project {gate.project_id} not found",
        )
    if project.status == ProjectStatus.CANCELLED:
        raise HTTPException(
            status_code=400,
            detail="Cannot modify approval gates on a cancelled project",
        )
    return project


def _queue_next_task(project: Project, db: Session) -> None:
    """Find the next PENDING task for the project and queue it via Celery."""
    pending_tasks = db.scalars(
        select(AgentTask)
        .where(
            AgentTask.project_id == project.id,
            AgentTask.status == AgentTaskStatus.PENDING,
        )
        .order_by(AgentTask.pipeline_order)
    ).all()

    if not pending_tasks:
        log.info("project_pipeline_complete", project_id=project.id)
        project.status = ProjectStatus.COMPLETED
        project.completed_at = datetime.now(UTC).replace(tzinfo=None)
        db.commit()
        return

    next_task = pending_tasks[0]
    try:
        from backend.tasks.pipeline_tasks import run_content_agent  # noqa: PLC0415

        celery_result = run_content_agent.delay(
            project_id=project.id,
            task_id=next_task.id,
        )
        next_task.celery_task_id = celery_result.id
        next_task.status = AgentTaskStatus.PENDING
        db.commit()
        log.info(
            "next_task_queued",
            project_id=project.id,
            task_id=next_task.id,
            agent=next_task.agent_name,
        )
    except Exception as exc:
        log.error(
            "next_task_queue_failed",
            project_id=project.id,
            task_id=next_task.id,
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/", response_model=list[ApprovalGateOut])
def list_pending_approvals(
    db: Session = Depends(get_session),
) -> list[ApprovalGateOut]:
    """Return all pending approval gates across all projects."""
    gates = db.scalars(
        select(ApprovalGate)
        .where(ApprovalGate.status == ApprovalGateStatus.PENDING)
        .order_by(ApprovalGate.created_at)
    ).all()
    return [_gate_to_out(g) for g in gates]


@router.get("/{gate_id}", response_model=ApprovalGateOut)
def get_gate(
    gate_id: int,
    db: Session = Depends(get_session),
) -> ApprovalGateOut:
    """Return a single approval gate by ID."""
    gate = _get_gate_or_404(gate_id, db)
    return _gate_to_out(gate)


@router.post("/{gate_id}/approve")
def approve_gate(
    gate_id: int,
    data: ApprovalAction,
    db: Session = Depends(get_session),
) -> dict:
    """Approve an approval gate, unblocking the next pipeline task.

    Idempotent: if the gate is already approved, returns 200 without
    re-triggering the pipeline.
    """
    gate = _get_gate_or_404(gate_id, db)
    project = _assert_project_not_cancelled(gate, db)

    if gate.status == ApprovalGateStatus.APPROVED:
        log.info("gate_already_approved", gate_id=gate_id)
        return {"detail": "Gate already approved", "gate_id": gate_id}

    if gate.status == ApprovalGateStatus.REJECTED:
        raise HTTPException(
            status_code=400,
            detail="Cannot approve a rejected gate — create a new review cycle instead",
        )

    if gate.gate_name == "site_review":
        content_gates = db.scalars(
            select(ApprovalGate).where(
                ApprovalGate.project_id == project.id,
                ApprovalGate.gate_name == "content_review",
            )
        ).all()
        unapproved = [g for g in content_gates if g.status != ApprovalGateStatus.APPROVED]
        if unapproved:
            raise HTTPException(
                status_code=400,
                detail="content_review gate(s) must be approved before approving site_review",
            )

    gate.status = ApprovalGateStatus.APPROVED
    gate.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
    gate.reviewed_by = data.reviewed_by
    if data.notes:
        gate.notes = data.notes
    db.commit()

    log.info(
        "gate_approved",
        gate_id=gate_id,
        gate_name=gate.gate_name,
        project_id=project.id,
        reviewed_by=data.reviewed_by,
    )

    _queue_next_task(project, db)

    return {
        "detail": "Gate approved",
        "gate_id": gate_id,
        "gate_name": gate.gate_name,
        "project_id": project.id,
    }


@router.post("/{gate_id}/reject")
def reject_gate(
    gate_id: int,
    data: ApprovalReject,
    db: Session = Depends(get_session),
) -> dict:
    """Reject an approval gate with required notes."""
    gate = _get_gate_or_404(gate_id, db)
    project = _assert_project_not_cancelled(gate, db)

    if gate.status in (ApprovalGateStatus.APPROVED,):
        raise HTTPException(
            status_code=400,
            detail="Cannot reject an already-approved gate",
        )

    gate.status = ApprovalGateStatus.REJECTED
    gate.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
    gate.reviewed_by = data.reviewed_by
    gate.notes = data.notes

    project.status = ProjectStatus.NEEDS_INPUT
    db.commit()

    log.info(
        "gate_rejected",
        gate_id=gate_id,
        gate_name=gate.gate_name,
        project_id=project.id,
        reviewed_by=data.reviewed_by,
    )

    return {
        "detail": "Gate rejected — project put on hold",
        "gate_id": gate_id,
        "gate_name": gate.gate_name,
        "project_id": project.id,
    }


@router.post("/{gate_id}/request-revision")
def request_revision(
    gate_id: int,
    data: ApprovalReject,
    db: Session = Depends(get_session),
) -> dict:
    """Request a content revision — partially re-runs the content agent for flagged pages."""
    gate = _get_gate_or_404(gate_id, db)
    project = _assert_project_not_cancelled(gate, db)

    if gate.gate_name not in ("content_review", "site_review"):
        raise HTTPException(
            status_code=400,
            detail=f"Revision requests are only valid for content_review or site_review gates, "
                   f"not '{gate.gate_name}'",
        )

    gate.status = ApprovalGateStatus.REVISION_REQUESTED
    gate.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
    gate.reviewed_by = data.reviewed_by
    gate.notes = data.notes

    project.status = ProjectStatus.RUNNING

    db.commit()

    content_tasks = db.scalars(
        select(AgentTask).where(
            AgentTask.project_id == project.id,
            AgentTask.agent_name.contains("content"),
        )
    ).all()

    if content_tasks:
        last_task = content_tasks[-1]
        last_task.status = AgentTaskStatus.PENDING
        last_task.retry_count += 1
        last_task.error = None
        last_task.started_at = None
        last_task.completed_at = None
        db.commit()

        try:
            from backend.tasks.pipeline_tasks import run_content_agent  # noqa: PLC0415

            celery_result = run_content_agent.delay(
                project_id=project.id,
                task_id=last_task.id,
            )
            last_task.celery_task_id = celery_result.id
            db.commit()
            log.info(
                "content_revision_queued",
                gate_id=gate_id,
                project_id=project.id,
                task_id=last_task.id,
            )
        except Exception as exc:
            log.error(
                "content_revision_queue_failed",
                gate_id=gate_id,
                project_id=project.id,
                error=str(exc),
            )

    log.info(
        "gate_revision_requested",
        gate_id=gate_id,
        gate_name=gate.gate_name,
        project_id=project.id,
        reviewed_by=data.reviewed_by,
    )

    return {
        "detail": "Revision requested — content agent re-queued",
        "gate_id": gate_id,
        "gate_name": gate.gate_name,
        "project_id": project.id,
    }
