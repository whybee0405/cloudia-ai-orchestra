from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BrandDNAAccessLog, Client, ICPPersona

router = APIRouter(prefix="/api/brand", tags=["reporting"])


@router.get("/clients/{client_id}/reports/brand-dna-usage")
def get_brand_dna_usage(
    client_id: UUID,
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
) -> dict:
    """Aggregated Brand DNA access statistics for a client."""
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    q = db.query(BrandDNAAccessLog).filter(BrandDNAAccessLog.client_id == client_id)
    if date_from:
        q = q.filter(BrandDNAAccessLog.accessed_at >= date_from)
    if date_to:
        q = q.filter(BrandDNAAccessLog.accessed_at <= date_to)

    logs = q.all()

    by_service: dict[str, int] = {}
    by_agent: dict[str, dict] = {}
    by_day: dict[str, int] = {}
    persona_usage: dict[int, int] = {}

    for entry in logs:
        svc = entry.accessed_by_service or "unknown"
        by_service[svc] = by_service.get(svc, 0) + 1

        agent_key = f"{svc}::{entry.accessed_by_agent or 'unknown'}"
        if agent_key not in by_agent:
            by_agent[agent_key] = {
                "agent_name": entry.accessed_by_agent or "unknown",
                "service": svc,
                "count": 0,
            }
        by_agent[agent_key]["count"] += 1

        if entry.accessed_at:
            d = entry.accessed_at.date().isoformat()
            by_day[d] = by_day.get(d, 0) + 1

        for pid in (entry.persona_ids_used or []):
            persona_usage[pid] = persona_usage.get(pid, 0) + 1

    # Resolve persona names
    persona_ids = list(persona_usage.keys())
    personas_by_id = {}
    if persona_ids:
        rows = db.query(ICPPersona).filter(ICPPersona.id.in_(persona_ids)).all()
        personas_by_id = {p.id: p.persona_name for p in rows}

    persona_usage_list = [
        {
            "persona_id": pid,
            "persona_name": personas_by_id.get(pid, f"Persona {pid}"),
            "access_count": count,
        }
        for pid, count in sorted(persona_usage.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "client_id": str(client_id),
        "total_accesses": len(logs),
        "by_service": by_service,
        "by_agent": sorted(by_agent.values(), key=lambda x: x["count"], reverse=True),
        "by_day": [{"date": d, "count": c} for d, c in sorted(by_day.items())],
        "persona_usage": persona_usage_list,
    }
