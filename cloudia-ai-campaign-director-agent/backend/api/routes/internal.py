"""Internal routes — consumed by the Brand DNA Director agent only."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.db.models import Campaign, Client, ContentAsset
from backend.db.session import get_db

router = APIRouter(prefix="/internal", tags=["internal"])


def _verify_internal(x_internal_secret: str = Header(default="")) -> None:
    secret = get_settings().internal_api_secret
    if secret and x_internal_secret != secret:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/health")
def internal_health() -> dict:
    return {"status": "ok", "service": "campaign-director"}


@router.get("/summary", dependencies=[Depends(_verify_internal)])
def internal_summary(db: Session = Depends(get_db)) -> dict:
    active = db.scalar(
        select(func.count()).select_from(Campaign).where(Campaign.status == "active")
    ) or 0
    total_clients = db.scalar(select(func.count()).select_from(Client)) or 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent_assets = db.scalar(
        select(func.count())
        .select_from(ContentAsset)
        .where(ContentAsset.created_at >= cutoff)
    ) or 0
    return {
        "service": "campaign-director",
        "active_campaigns": active,
        "total_clients": total_clients,
        "recent_assets_7d": recent_assets,
    }
