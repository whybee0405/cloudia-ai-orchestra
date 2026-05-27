from datetime import timedelta
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
