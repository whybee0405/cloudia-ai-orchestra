from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from backend.api.schemas import (
    CampaignCreate,
    CampaignListItem,
    CampaignRead,
    CampaignUpdate,
)
from backend.db.models import AgentTask, Campaign, ContentCalendar, ScheduledPost
from backend.db.session import get_db

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignRead, status_code=201)
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db)):
    from backend.tasks.pipeline_tasks import run_director

    campaign = Campaign(**payload.model_dump())
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    run_director.delay(campaign.id)

    return _load_full(campaign.id, db)


@router.get("", response_model=list[CampaignListItem])
def list_campaigns(
    client_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Campaign)
    if client_id is not None:
        q = q.filter(Campaign.client_id == client_id)
    return q.order_by(Campaign.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{campaign_id}", response_model=CampaignRead)
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    return _load_full(campaign_id, db)


@router.patch("/{campaign_id}", response_model=CampaignRead)
def update_campaign(
    campaign_id: int,
    payload: CampaignUpdate,
    db: Session = Depends(get_db),
):
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(campaign, key, value)

    db.commit()
    return _load_full(campaign_id, db)


@router.post("/{campaign_id}/pause", response_model=CampaignRead)
def pause_campaign(campaign_id: int, db: Session = Depends(get_db)):
    from backend.tasks.celery_app import celery_app

    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")

    tasks = (
        db.query(AgentTask)
        .filter(
            AgentTask.campaign_id == campaign_id,
            AgentTask.status.in_(["pending", "started"]),
        )
        .all()
    )
    for task in tasks:
        if task.celery_task_id:
            celery_app.control.revoke(task.celery_task_id, terminate=True)
        task.status = "revoked"

    scheduled_posts = (
        db.query(ScheduledPost)
        .join(ContentCalendar, ScheduledPost.calendar_id == ContentCalendar.id)
        .filter(
            ContentCalendar.campaign_id == campaign_id,
            ScheduledPost.status == "queued",
        )
        .all()
    )
    for post in scheduled_posts:
        if post.celery_task_id:
            celery_app.control.revoke(post.celery_task_id, terminate=False)
        post.status = "cancelled"

    campaign.status = "paused"
    db.commit()
    return _load_full(campaign_id, db)


@router.post("/{campaign_id}/resume", response_model=CampaignRead)
def resume_campaign(campaign_id: int, db: Session = Depends(get_db)):
    from backend.tasks.scheduled_tasks import publish_post

    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")

    now = datetime.now(timezone.utc)
    pending_posts = (
        db.query(ScheduledPost)
        .join(ContentCalendar, ScheduledPost.calendar_id == ContentCalendar.id)
        .filter(
            ContentCalendar.campaign_id == campaign_id,
            ScheduledPost.status == "cancelled",
            ScheduledPost.scheduled_for > now,
        )
        .all()
    )
    for post in pending_posts:
        eta = post.scheduled_for
        result = publish_post.apply_async(args=[post.id], eta=eta)
        post.celery_task_id = result.id
        post.status = "queued"

    campaign.status = "active"
    db.commit()
    return _load_full(campaign_id, db)


def _load_full(campaign_id: int, db: Session) -> Campaign:
    campaign = (
        db.query(Campaign)
        .options(
            joinedload(Campaign.calendar_items),
            joinedload(Campaign.content_assets),
            joinedload(Campaign.approval_gates),
        )
        .filter(Campaign.id == campaign_id)
        .first()
    )
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    return campaign
