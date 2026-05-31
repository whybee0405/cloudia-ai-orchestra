import uuid
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Client, BrandDNA
from app.media import storage

router = APIRouter(prefix="/api/clients/{client_id}", tags=["logo"])

_ALLOWED = {"image/png", "image/jpeg", "image/svg+xml", "image/webp"}
_MAX_BYTES = 5 * 1024 * 1024


@router.post("/logo")
async def upload_logo(client_id: UUID, file: UploadFile = File(...), db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if file.content_type not in _ALLOWED:
        raise HTTPException(status_code=400, detail=f"Unsupported type: {file.content_type}")

    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds 5 MB limit")

    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "png"
    object_path = f"logos/{client_id}/{uuid.uuid4()}.{ext}"
    logo_url = storage.upload(data, object_path, file.content_type)

    if client.brand_dna:
        client.brand_dna.logo_url = logo_url
        client.brand_dna.updated_at = datetime.now(timezone.utc)
    else:
        db.add(BrandDNA(client_id=client_id, logo_url=logo_url))

    db.commit()
    return {"logo_url": logo_url}
