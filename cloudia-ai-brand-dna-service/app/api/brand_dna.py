from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Client, BrandDNA
from app.schemas import BrandDNAUpdate, BrandDNAResponse, EnrichmentResponse
from app.agents.enrichment import run_enrichment

router = APIRouter(prefix="/api/clients/{client_id}/brand-dna", tags=["brand-dna"])


def _get_client_or_404(client_id: UUID, db: Session) -> Client:
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.get("", response_model=BrandDNAResponse)
def get_brand_dna(client_id: UUID, db: Session = Depends(get_db)):
    client = _get_client_or_404(client_id, db)
    if not client.brand_dna:
        raise HTTPException(status_code=404, detail="Brand DNA not yet created for this client")
    return client.brand_dna


@router.put("", response_model=BrandDNAResponse)
def save_brand_dna(client_id: UUID, body: BrandDNAUpdate, db: Session = Depends(get_db)):
    client = _get_client_or_404(client_id, db)

    if client.brand_dna:
        dna = client.brand_dna
        for field, value in body.model_dump(exclude_none=True).items():
            setattr(dna, field, value)
        dna.updated_at = datetime.now(timezone.utc)
    else:
        dna = BrandDNA(client_id=client_id, **body.model_dump(exclude_none=True))
        db.add(dna)

    db.commit()
    db.refresh(dna)
    return dna


@router.post("/enrich", response_model=EnrichmentResponse)
def enrich_brand_dna(client_id: UUID, db: Session = Depends(get_db)):
    client = _get_client_or_404(client_id, db)

    brand_dna_dict = {}
    if client.brand_dna:
        dna = client.brand_dna
        brand_dna_dict = {
            "tagline": dna.tagline,
            "tone": dna.tone,
            "language_style": dna.language_style,
            "personality_traits": dna.personality_traits,
            "visual_style": dna.visual_style,
            "usps": dna.usps,
            "pain_points_addressed": dna.pain_points_addressed,
            "key_messages": dna.key_messages,
            "competitors": dna.competitors,
            "differentiators": dna.differentiators,
        }

    result = run_enrichment(
        client_name=client.name,
        industry=client.industry,
        website_url=client.website_url,
        brand_dna=brand_dna_dict,
    )

    if client.brand_dna:
        client.brand_dna.enriched_at = datetime.now(timezone.utc)
        db.commit()

    return result
