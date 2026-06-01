from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.db.models import AgentTask, Campaign
from backend.db.session import get_db

router = APIRouter(prefix="/reporting", tags=["reporting"])


@router.get("/agent-costs")
def get_agent_costs(
    client_id: int = Query(...),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
) -> dict:
    """Aggregated Claude API token/cost usage for campaign agent tasks."""
    q = (
        db.query(AgentTask)
        .join(Campaign, AgentTask.campaign_id == Campaign.id)
        .filter(Campaign.client_id == client_id)
    )
    if date_from:
        q = q.filter(AgentTask.started_at >= date_from)
    if date_to:
        q = q.filter(AgentTask.started_at <= date_to)

    tasks = q.all()

    by_agent: dict[str, dict] = {}
    by_day: dict[str, dict] = {}
    total_tokens = 0
    total_cost = 0.0

    for t in tasks:
        name = t.agent_name or "unknown"
        if name not in by_agent:
            by_agent[name] = {"agent_name": name, "runs": 0, "tokens": 0, "cost_usd": 0.0}
        by_agent[name]["runs"] += 1
        if t.tokens_used:
            by_agent[name]["tokens"] += t.tokens_used
            total_tokens += t.tokens_used
        if t.cost_usd:
            by_agent[name]["cost_usd"] += float(t.cost_usd)
            total_cost += float(t.cost_usd)

        if t.started_at:
            d = t.started_at.date().isoformat()
            if d not in by_day:
                by_day[d] = {"date": d, "cost_usd": 0.0, "tokens": 0}
            if t.tokens_used:
                by_day[d]["tokens"] += t.tokens_used
            if t.cost_usd:
                by_day[d]["cost_usd"] += float(t.cost_usd)

    return {
        "service": "campaign-director",
        "period_cost_usd": round(total_cost, 4),
        "period_tokens": total_tokens,
        "by_agent": sorted(by_agent.values(), key=lambda x: x["cost_usd"], reverse=True),
        "by_day": sorted(by_day.values(), key=lambda x: x["date"]),
    }
