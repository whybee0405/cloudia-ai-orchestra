from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.schemas import CalendarItemRead, CalendarItemUpdate
from backend.db.models import ContentCalendar
from backend.db.session import get_db

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("", response_model=list[CalendarItemRead])
def list_calendar_items(
    client_id: Optional[int] = Query(None),
    campaign_id: Optional[int] = Query(None),
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(ContentCalendar)
    if client_id is not None:
        q = q.filter(ContentCalendar.client_id == client_id)
    if campaign_id is not None:
        q = q.filter(ContentCalendar.campaign_id == campaign_id)
    if platform is not None:
        q = q.filter(ContentCalendar.platform == platform)
    if status is not None:
        q = q.filter(ContentCalendar.status == status)
    return q.order_by(ContentCalendar.scheduled_for).offset(skip).limit(limit).all()


@router.patch("/{item_id}", response_model=CalendarItemRead)
def update_calendar_item(
    item_id: int,
    payload: CalendarItemUpdate,
    db: Session = Depends(get_db),
):
    item = db.get(ContentCalendar, item_id)
    if not item:
        raise HTTPException(404, "Calendar item not found")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def delete_calendar_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(ContentCalendar, item_id)
    if not item:
        raise HTTPException(404, "Calendar item not found")
    db.delete(item)
    db.commit()
