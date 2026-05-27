from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Client
from app.schemas import ClientCreate, ClientUpdate, ClientResponse

router = APIRouter(prefix="/api/clients", tags=["clients"])


def _to_response(client: Client) -> ClientResponse:
    return ClientResponse(
        id=client.id,
        name=client.name,
        website_url=client.website_url,
        industry=client.industry,
        sub_industry=client.sub_industry,
        location=client.location,
        timezone=client.timezone,
        founded_year=client.founded_year,
        is_active=client.is_active,
        created_at=client.created_at,
        updated_at=client.updated_at,
        has_brand_dna=client.brand_dna is not None,
        persona_count=len(client.personas),
    )


@router.get("", response_model=list[ClientResponse])
def list_clients(active_only: bool = True, db: Session = Depends(get_db)):
    q = db.query(Client)
    if active_only:
        q = q.filter(Client.is_active.is_(True))
    return [_to_response(c) for c in q.order_by(Client.name).all()]


@router.post("", response_model=ClientResponse, status_code=201)
def create_client(body: ClientCreate, db: Session = Depends(get_db)):
    client = Client(**body.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return _to_response(client)


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: UUID, db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return _to_response(client)


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(client_id: UUID, body: ClientUpdate, db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(client, field, value)
    client.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(client)
    return _to_response(client)
