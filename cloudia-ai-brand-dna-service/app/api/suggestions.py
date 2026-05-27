from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Client
from app.schemas import SuggestionsResponse
from app.agents.director import run_director

router = APIRouter(prefix="/api/clients/{client_id}/suggestions", tags=["suggestions"])


@router.get("", response_model=SuggestionsResponse)
def get_suggestions(client_id: UUID, db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return run_director(
        client_id=client.id,
        client_name=client.name,
        has_brand_dna=client.brand_dna is not None,
        persona_count=len(client.personas),
    )
