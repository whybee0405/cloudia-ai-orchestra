"""
Projects and Clients routes for the CloudIA API.

/api/projects  — list, create, get, cancel, retry
/api/projects/clients  — create and list clients
"""

from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.api.schemas import (
    AgentTaskOut,
    ApprovalGateOut,
    ClientCreate,
    ClientOut,
    ProjectCreate,
    ProjectOut,
)
from backend.db.models import (
    AgentTask,
    AgentTaskStatus,
    ApprovalGate,
    Client,
    Project,
    ProjectStatus,
)
from backend.db.session import get_session

log = structlog.get_logger()

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers — ORM → schema mapping
# ---------------------------------------------------------------------------


def _project_to_out(project: Project) -> ProjectOut:
    tasks = [
        AgentTaskOut(
            id=t.id,
            agent_name=t.agent_name,
            pipeline_order=t.pipeline_order,
            status=t.status,
            tokens_used=t.tokens_used,
            cost_usd=float(t.cost_usd) if t.cost_usd is not None else None,
            started_at=t.started_at,
            completed_at=t.completed_at,
            error=t.error,
            retry_count=t.retry_count,
        )
        for t in (project.agent_tasks or [])
    ]

    gates = [
        ApprovalGateOut(
            id=g.id,
            gate_name=g.gate_name,
            pipeline_order=g.pipeline_order,
            status=g.status,
            notes=g.notes,
            created_at=g.created_at,
            reviewed_at=g.reviewed_at,
            reviewed_by=g.reviewed_by,
        )
        for g in (project.approval_gates or [])
    ]

    return ProjectOut(
        id=project.id,
        client_id=project.client_id,
        platform=project.platform,
        status=project.status,
        brief=project.brief,
        pipeline_plan=project.pipeline_plan,
        site_url=project.site_url,
        estimated_pages=project.estimated_pages,
        actual_pages=project.actual_pages,
        created_at=project.created_at,
        completed_at=project.completed_at,
        operator_notes=project.operator_notes,
        tasks=tasks,
        gates=gates,
    )


def _client_to_out(client: Client) -> ClientOut:
    return ClientOut(
        id=client.id,
        name=client.name,
        industry=client.industry,
        business_type=client.business_type,
        target_audience=client.target_audience,
        usp=client.usp,
        tone_of_voice=client.tone_of_voice,
        brand_colours=client.brand_colours,
        brand_fonts=client.brand_fonts,
        logo_url=client.logo_url,
        contact_email=client.contact_email,
        contact_phone=client.contact_phone,
        address=client.address,
        city=client.city,
        country=client.country,
        website_url=client.website_url,
        social_links=client.social_links,
        notes=client.notes,
        brand_dna_client_id=getattr(client, 'brand_dna_client_id', None),
        created_at=client.created_at,
    )


# ---------------------------------------------------------------------------
# Project endpoints
# ---------------------------------------------------------------------------


@router.get("/", response_model=list[ProjectOut])
def list_projects(
    status: Optional[str] = None,
    db: Session = Depends(get_session),
) -> list[ProjectOut]:
    """Return all non-cancelled projects, optionally filtered by status."""
    stmt = (
        select(Project)
        .where(Project.status != ProjectStatus.CANCELLED)
        .options(
            selectinload(Project.agent_tasks),
            selectinload(Project.approval_gates),
        )
        .order_by(Project.created_at.desc())
    )
    if status:
        if status not in ProjectStatus.STATUS_CHOICES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{status}'. Valid values: {ProjectStatus.STATUS_CHOICES}",
            )
        stmt = stmt.where(Project.status == status)

    projects = db.scalars(stmt).all()
    return [_project_to_out(p) for p in projects]


@router.post("/", response_model=ProjectOut, status_code=201)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_session),
) -> ProjectOut:
    """Create a project and trigger the Director agent synchronously."""
    client = db.get(Client, data.client_id)
    if client is None:
        raise HTTPException(
            status_code=404,
            detail=f"Client {data.client_id} not found",
        )

    platform = data.platform
    if not platform:
        platform = data.brief.get("platform", "wordpress")

    project = Project(
        client_id=data.client_id,
        platform=platform,
        status=ProjectStatus.PLANNED,
        brief=data.brief,
    )
    db.add(project)
    db.flush()

    log.info("project_creating", project_id=project.id, client_id=data.client_id)

    try:
        from backend.agents.director import DirectorAgent  # noqa: PLC0415

        director = DirectorAgent(
            client_id=data.client_id,
            raw_brief=data.brief,
        )
        analysis = director.analyze()

        project.pipeline_plan = analysis.get("pipeline_plan") or analysis
        project.status = ProjectStatus.RUNNING
        project.estimated_pages = analysis.get("estimated_pages")
    except Exception as exc:
        log.error("director_agent_failed", project_id=project.id, error=str(exc))
        project.status = ProjectStatus.PLANNED
        project.operator_notes = f"Director error: {exc}"

    db.commit()
    db.refresh(project)

    log.info(
        "project_created",
        project_id=project.id,
        platform=platform,
        status=project.status,
    )
    return _project_to_out(project)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    db: Session = Depends(get_session),
) -> ProjectOut:
    """Return a project with all its agent tasks and approval gates."""
    stmt = (
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.agent_tasks),
            selectinload(Project.approval_gates),
        )
    )
    project = db.scalars(stmt).first()
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return _project_to_out(project)


@router.delete("/{project_id}")
def cancel_project(
    project_id: int,
    db: Session = Depends(get_session),
) -> dict:
    """Soft-delete: set status=cancelled. Does not remove from DB."""
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

    if project.status == ProjectStatus.CANCELLED:
        return {"detail": "Project is already cancelled", "project_id": project_id}

    old_status = project.status
    project.status = ProjectStatus.CANCELLED
    db.commit()

    log.info("project_cancelled", project_id=project_id, previous_status=old_status)
    return {"detail": "Project cancelled", "project_id": project_id}


@router.post("/{project_id}/retry/{task_id}")
def retry_task(
    project_id: int,
    task_id: int,
    db: Session = Depends(get_session),
) -> dict:
    """Re-queue a failed agent task via Celery."""
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    if project.status == ProjectStatus.CANCELLED:
        raise HTTPException(
            status_code=400,
            detail="Cannot retry tasks on a cancelled project",
        )

    stmt = select(AgentTask).where(
        AgentTask.id == task_id,
        AgentTask.project_id == project_id,
    )
    task = db.scalars(stmt).first()
    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found on project {project_id}",
        )

    if task.status != AgentTaskStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail=f"Task {task_id} has status '{task.status}' — only 'failed' tasks can be retried",
        )

    task.status = AgentTaskStatus.PENDING
    task.retry_count += 1
    task.error = None
    task.started_at = None
    task.completed_at = None
    db.commit()

    try:
        from backend.tasks.pipeline_tasks import run_content_agent  # noqa: PLC0415

        celery_task = run_content_agent.delay(
            project_id=project_id,
            task_id=task_id,
        )
        task.celery_task_id = celery_task.id
        db.commit()
        log.info(
            "task_requeued",
            project_id=project_id,
            task_id=task_id,
            celery_task_id=celery_task.id,
            retry_count=task.retry_count,
        )
    except Exception as exc:
        log.error("task_requeue_failed", task_id=task_id, error=str(exc))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue task: {exc}",
        ) from exc

    return {
        "detail": "Task re-queued",
        "task_id": task_id,
        "project_id": project_id,
        "retry_count": task.retry_count,
    }


# ---------------------------------------------------------------------------
# Client endpoints
# ---------------------------------------------------------------------------


@router.post("/clients/", response_model=ClientOut, status_code=201)
def create_client(
    data: ClientCreate,
    db: Session = Depends(get_session),
) -> ClientOut:
    """Create a new client record."""
    if data.contact_email:
        existing = db.scalars(
            select(Client).where(Client.contact_email == data.contact_email)
        ).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"A client with email '{data.contact_email}' already exists (id={existing.id})",
            )

    client = Client(
        name=data.name,
        industry=data.industry,
        business_type=data.business_type,
        target_audience=data.target_audience,
        usp=data.usp,
        tone_of_voice=data.tone_of_voice,
        brand_colours=data.brand_colours,
        brand_fonts=data.brand_fonts,
        logo_url=data.logo_url,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        address=data.address,
        city=data.city,
        country=data.country,
        website_url=data.website_url,
        social_links=data.social_links,
        notes=data.notes,
        brand_dna_client_id=data.brand_dna_client_id,
    )
    db.add(client)
    db.commit()
    db.refresh(client)

    log.info("client_created", client_id=client.id, name=data.name)
    return _client_to_out(client)


@router.get("/clients/by-brand-dna/{brand_dna_client_id}", response_model=ClientOut)
def get_client_by_brand_dna(
    brand_dna_client_id: str,
    db: Session = Depends(get_session),
) -> ClientOut:
    """Look up a WebDev client by its Brand DNA UUID."""
    client = db.scalars(
        select(Client).where(Client.brand_dna_client_id == brand_dna_client_id)
    ).first()
    if client is None:
        raise HTTPException(
            status_code=404,
            detail="No WebDev client linked to this Brand DNA client",
        )
    return _client_to_out(client)


@router.get("/clients/", response_model=list[ClientOut])
def list_clients(
    db: Session = Depends(get_session),
) -> list[ClientOut]:
    """Return all clients."""
    clients = db.scalars(
        select(Client).order_by(Client.created_at.desc())
    ).all()
    return [_client_to_out(c) for c in clients]
