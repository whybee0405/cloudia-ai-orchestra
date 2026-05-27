from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.schemas import ScheduledPostRead
from backend.db.models import ContentCalendar, PlatformAccount, ScheduledPost
from backend.db.session import get_db

router = APIRouter(prefix="/publishing", tags=["publishing"])


@router.get("/scheduled", response_model=list[ScheduledPostRead])
def list_scheduled_posts(
    client_id: Optional[int] = Query(None),
    campaign_id: Optional[int] = Query(None),
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(ScheduledPost)

    if campaign_id is not None:
        q = q.join(ContentCalendar, ScheduledPost.calendar_id == ContentCalendar.id).filter(
            ContentCalendar.campaign_id == campaign_id
        )

    if client_id is not None:
        if campaign_id is None:
            q = q.join(ContentCalendar, ScheduledPost.calendar_id == ContentCalendar.id)
        q = q.filter(ContentCalendar.client_id == client_id)

    if platform is not None:
        already_joined = campaign_id is not None or client_id is not None
        if not already_joined:
            q = q.join(
                PlatformAccount,
                ScheduledPost.platform_account_id == PlatformAccount.id,
            )
        else:
            q = q.join(
                PlatformAccount,
                ScheduledPost.platform_account_id == PlatformAccount.id,
            )
        q = q.filter(PlatformAccount.platform == platform)

    if status is not None:
        q = q.filter(ScheduledPost.status == status)

    return q.order_by(ScheduledPost.scheduled_for).offset(skip).limit(limit).all()


@router.post("/scheduled/{post_id}/cancel", response_model=ScheduledPostRead)
def cancel_scheduled_post(post_id: int, db: Session = Depends(get_db)):
    from backend.tasks.celery_app import celery_app

    post = db.get(ScheduledPost, post_id)
    if not post:
        raise HTTPException(404, "Scheduled post not found")
    if post.status not in ("queued", "pending"):
        raise HTTPException(409, f"Post is already {post.status} and cannot be cancelled")

    if post.celery_task_id:
        celery_app.control.revoke(post.celery_task_id, terminate=False)

    post.status = "cancelled"
    db.commit()
    db.refresh(post)
    return post
