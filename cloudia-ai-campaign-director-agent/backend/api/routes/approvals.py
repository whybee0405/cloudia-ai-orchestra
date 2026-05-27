from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.schemas import ApprovalAction, ApprovalGateRead
from backend.db.models import ApprovalGate, Campaign
from backend.db.session import get_db

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalGateRead])
def list_pending_approvals(
    campaign_id: Optional[int] = Query(None),
    status: Optional[str] = Query("pending"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(ApprovalGate)
    if campaign_id is not None:
        q = q.filter(ApprovalGate.campaign_id == campaign_id)
    if status is not None:
        q = q.filter(ApprovalGate.status == status)
    return q.order_by(ApprovalGate.created_at).offset(skip).limit(limit).all()


@router.post("/{gate_id}/approve", response_model=ApprovalGateRead)
def approve_gate(
    gate_id: int,
    payload: ApprovalAction,
    db: Session = Depends(get_db),
):
    gate = db.get(ApprovalGate, gate_id)
    if not gate:
        raise HTTPException(404, "Approval gate not found")
    if gate.status != "pending":
        raise HTTPException(409, f"Gate is already {gate.status}")

    gate.status = "approved"
    gate.notes = payload.notes
    gate.reviewed_by = payload.reviewed_by
    gate.reviewed_at = datetime.now(timezone.utc)
    db.commit()

    _trigger_next_stage(gate, db)

    db.refresh(gate)
    return gate


@router.post("/{gate_id}/reject", response_model=ApprovalGateRead)
def reject_gate(
    gate_id: int,
    payload: ApprovalAction,
    db: Session = Depends(get_db),
):
    gate = db.get(ApprovalGate, gate_id)
    if not gate:
        raise HTTPException(404, "Approval gate not found")
    if gate.status != "pending":
        raise HTTPException(409, f"Gate is already {gate.status}")

    gate.status = "rejected"
    gate.notes = payload.notes
    gate.reviewed_by = payload.reviewed_by
    gate.reviewed_at = datetime.now(timezone.utc)

    campaign = db.get(Campaign, gate.campaign_id)
    if campaign:
        campaign.status = "halted"

    db.commit()
    db.refresh(gate)
    return gate


def _trigger_next_stage(gate: ApprovalGate, db: Session) -> None:
    from backend.tasks.pipeline_tasks import run_planner

    if gate.gate_name == "brief_approved":
        run_planner.delay(gate.campaign_id)
