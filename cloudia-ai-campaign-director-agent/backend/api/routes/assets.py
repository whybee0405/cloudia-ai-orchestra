from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.schemas import AssetListItem, AssetRead, AssetUpdate
from backend.db.models import ContentAsset
from backend.db.session import get_db

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[AssetListItem])
def list_assets(
    campaign_id: Optional[int] = Query(None),
    client_id: Optional[int] = Query(None),
    asset_type: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(ContentAsset)
    if campaign_id is not None:
        q = q.filter(ContentAsset.campaign_id == campaign_id)
    if client_id is not None:
        q = q.filter(ContentAsset.client_id == client_id)
    if asset_type is not None:
        q = q.filter(ContentAsset.asset_type == asset_type)
    if platform is not None:
        q = q.filter(ContentAsset.content_type == platform)
    if status is not None:
        q = q.filter(ContentAsset.status == status)
    return q.order_by(ContentAsset.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/report")
def get_asset_report(
    client_id: int = Query(...),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
) -> dict:
    """Aggregated asset production stats for a client."""
    q = db.query(ContentAsset).filter(ContentAsset.client_id == client_id)
    if date_from:
        q = q.filter(ContentAsset.created_at >= date_from)
    if date_to:
        q = q.filter(ContentAsset.created_at <= date_to)

    assets = q.all()

    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    by_date: dict[str, dict] = {}
    total_tokens = 0
    total_cost = 0.0
    brand_check_count = 0
    brand_check_pass = 0

    for a in assets:
        s = a.status or "unknown"
        by_status[s] = by_status.get(s, 0) + 1
        t = a.asset_type or "unknown"
        by_type[t] = by_type.get(t, 0) + 1
        if a.tokens_used:
            total_tokens += a.tokens_used
        if a.cost_usd:
            total_cost += float(a.cost_usd)
        if a.brand_check_passed is not None:
            brand_check_count += 1
            if a.brand_check_passed:
                brand_check_pass += 1
        if a.created_at:
            d = a.created_at.date().isoformat()
            if d not in by_date:
                by_date[d] = {"date": d, "count": 0, "cost_usd": 0.0}
            by_date[d]["count"] += 1
            if a.cost_usd:
                by_date[d]["cost_usd"] += float(a.cost_usd)

    return {
        "total_assets": len(assets),
        "by_status": by_status,
        "by_type": by_type,
        "brand_check_pass_rate": round(brand_check_pass / brand_check_count, 3) if brand_check_count else None,
        "cost_usd_total": round(total_cost, 4),
        "tokens_total": total_tokens,
        "by_date": sorted(by_date.values(), key=lambda x: x["date"]),
    }


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.get(ContentAsset, asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    return asset


@router.get("/{asset_id}/url")
def get_asset_url(asset_id: int, db: Session = Depends(get_db)):
    from backend.media.storage import signed_url

    asset = db.get(ContentAsset, asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    if not asset.storage_path:
        raise HTTPException(404, "Asset has no storage path")

    try:
        url = signed_url(
            object_path=asset.storage_path,
            expires=timedelta(hours=1),
            client_id_prefix=str(asset.client_id),
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc))

    return {"url": url, "expires_in_seconds": 3600}


@router.patch("/{asset_id}", response_model=AssetRead)
def update_asset(
    asset_id: int,
    payload: AssetUpdate,
    db: Session = Depends(get_db),
):
    asset = db.get(ContentAsset, asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(asset, key, value)

    db.commit()
    db.refresh(asset)
    return asset
