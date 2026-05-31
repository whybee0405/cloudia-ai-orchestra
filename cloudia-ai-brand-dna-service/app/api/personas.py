from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Client, ICPPersona
from app.schemas import PersonaCreate, PersonaUpdate, PersonaResponse
from app.data.persona_templates import TEMPLATES, INDUSTRY_LABELS
from app.agents.persona_suggester import suggest_personas

router = APIRouter(prefix="/api/clients/{client_id}/personas", tags=["personas"])

MAX_PERSONAS = 5


def _get_client_or_404(client_id: UUID, db: Session) -> Client:
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.get("", response_model=list[PersonaResponse])
def list_personas(client_id: UUID, db: Session = Depends(get_db)):
    _get_client_or_404(client_id, db)
    return (
        db.query(ICPPersona)
        .filter(ICPPersona.client_id == client_id)
        .order_by(ICPPersona.order)
        .all()
    )


@router.post("", response_model=PersonaResponse, status_code=201)
def create_persona(client_id: UUID, body: PersonaCreate, db: Session = Depends(get_db)):
    client = _get_client_or_404(client_id, db)
    if len(client.personas) >= MAX_PERSONAS:
        raise HTTPException(status_code=400, detail=f"Maximum of {MAX_PERSONAS} personas allowed per client")
    persona = ICPPersona(client_id=client_id, **body.model_dump())
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return persona


@router.patch("/{persona_id}", response_model=PersonaResponse)
def update_persona(
    client_id: UUID, persona_id: int, body: PersonaUpdate, db: Session = Depends(get_db)
):
    _get_client_or_404(client_id, db)
    persona = db.get(ICPPersona, persona_id)
    if not persona or persona.client_id != client_id:
        raise HTTPException(status_code=404, detail="Persona not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(persona, field, value)
    persona.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(persona)
    return persona


@router.delete("/{persona_id}", status_code=204)
def delete_persona(client_id: UUID, persona_id: int, db: Session = Depends(get_db)):
    _get_client_or_404(client_id, db)
    persona = db.get(ICPPersona, persona_id)
    if not persona or persona.client_id != client_id:
        raise HTTPException(status_code=404, detail="Persona not found")
    db.delete(persona)
    db.commit()


@router.post("/suggest")
def suggest_persona_archetypes(client_id: UUID, db: Session = Depends(get_db)):
    client = _get_client_or_404(client_id, db)
    dna = client.brand_dna
    archetypes = suggest_personas(
        client_name=client.name,
        industry=client.industry,
        tagline=dna.tagline if dna else None,
        tone=dna.tone if dna else None,
        usps=dna.usps or [] if dna else [],
        key_messages=dna.key_messages or [] if dna else [],
    )
    return {"archetypes": archetypes}


@router.get("/templates")
def get_persona_templates(client_id: UUID, industry: str | None = None):
    if industry:
        templates = TEMPLATES.get(industry, [])
        return {"industry": industry, "templates": templates}
    return {
        "industries": [
            {"key": key, "label": label, "template_count": len(TEMPLATES.get(key, []))}
            for key, label in INDUSTRY_LABELS.items()
        ],
        "templates": TEMPLATES,
    }
