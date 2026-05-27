"""Internal endpoints — only accessible within the private network, not exposed via nginx."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional

from app.config import get_settings
from app.database import get_db
from app.models import Client
from app.schemas import BrandContext, PersonaContext, BrandDNAResponse, Suggestion, SuggestionsResponse
from app.agents.director import run_director

router = APIRouter(prefix="/internal", tags=["internal"])


def _require_secret(x_internal_secret: str = Header(default="")):
    settings = get_settings()
    if settings.internal_api_secret and x_internal_secret != settings.internal_api_secret:
        raise HTTPException(status_code=403, detail="Invalid internal secret")


def _build_prompt_block(client: Client) -> str:
    dna = client.brand_dna
    personas = client.personas

    lines = [f"=== BRAND DNA: {client.name} ==="]
    lines.append(f"Industry: {client.industry or 'Not specified'}")

    if dna:
        lines.append(f"Brand Voice: {dna.tone or '—'} — {dna.language_style or '—'}")
        if dna.personality_traits:
            lines.append(f"Personality: {', '.join(dna.personality_traits)}")
        if dna.visual_style:
            lines.append(f"Visual Style: {dna.visual_style}" + (f" | Primary Colour: {dna.primary_color}" if dna.primary_color else ""))
        if dna.usps:
            lines.append(f"USPs: {' | '.join(dna.usps)}")
        if dna.key_messages:
            lines.append(f"Key Messages: {' | '.join(dna.key_messages)}")
        if dna.differentiators:
            lines.append(f"Differentiators: {' | '.join(dna.differentiators)}")

    if personas:
        lines.append("\nTARGET PERSONAS:")
        for i, p in enumerate(personas, 1):
            age_range = f"{p.age_min}-{p.age_max}" if p.age_min and p.age_max else "—"
            lines.append(f"{i}. {p.persona_name} | Age: {age_range}")
            if p.pain_points:
                lines.append(f"   Pain Points: {', '.join(p.pain_points[:3])}")
            if p.goals:
                lines.append(f"   Goals: {', '.join(p.goals[:3])}")
            if p.seo_keywords:
                lines.append(f"   SEO Keywords: {', '.join(p.seo_keywords[:8])}")
            if p.vocabulary:
                lines.append(f"   Vocabulary: {', '.join(p.vocabulary[:6])}")

    lines.append("===============================")
    return "\n".join(lines)


@router.get("/health")
def health():
    return {"service": "brand-dna", "status": "ok"}


@router.get("/clients/{client_id}/brand-context", response_model=BrandContext)
def get_brand_context(
    client_id: UUID,
    db: Session = Depends(get_db),
    _: None = Depends(_require_secret),
):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    persona_contexts = [
        PersonaContext(
            persona_name=p.persona_name,
            age_range=f"{p.age_min}-{p.age_max}" if p.age_min and p.age_max else None,
            pain_points=p.pain_points,
            goals=p.goals,
            seo_keywords=p.seo_keywords,
            vocabulary=p.vocabulary,
            preferred_channels=p.preferred_channels,
        )
        for p in client.personas
    ]

    return BrandContext(
        client_id=client.id,
        client_name=client.name,
        industry=client.industry,
        brand_dna=client.brand_dna,
        personas=persona_contexts,
        prompt_block=_build_prompt_block(client),
    )
