from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID
from pydantic import BaseModel, HttpUrl, field_validator


# ── Client ────────────────────────────────────────────────────────────────────

class ClientCreate(BaseModel):
    name: str
    website_url: Optional[str] = None
    industry: Optional[str] = None
    sub_industry: Optional[str] = None
    location: Optional[str] = None
    timezone: str = "Africa/Johannesburg"
    founded_year: Optional[int] = None


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    website_url: Optional[str] = None
    industry: Optional[str] = None
    sub_industry: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None
    founded_year: Optional[int] = None
    is_active: Optional[bool] = None


class ClientResponse(BaseModel):
    id: UUID
    name: str
    website_url: Optional[str]
    industry: Optional[str]
    sub_industry: Optional[str]
    location: Optional[str]
    timezone: str
    founded_year: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    has_brand_dna: bool = False
    persona_count: int = 0

    model_config = {"from_attributes": True}


# ── Brand DNA ─────────────────────────────────────────────────────────────────

class BrandDNAUpdate(BaseModel):
    tagline: Optional[str] = None
    tone: Optional[str] = None
    language_style: Optional[str] = None
    personality_traits: Optional[List[str]] = None
    primary_color: Optional[str] = None
    secondary_colors: Optional[List[str]] = None
    accent_color: Optional[str] = None
    heading_font: Optional[str] = None
    body_font: Optional[str] = None
    logo_url: Optional[str] = None
    visual_style: Optional[str] = None
    usps: Optional[List[str]] = None
    pain_points_addressed: Optional[List[str]] = None
    key_messages: Optional[List[str]] = None
    competitors: Optional[List[str]] = None
    differentiators: Optional[List[str]] = None


class BrandDNAResponse(BaseModel):
    id: int
    client_id: UUID
    tagline: Optional[str]
    tone: Optional[str]
    language_style: Optional[str]
    personality_traits: Optional[List[str]]
    primary_color: Optional[str]
    secondary_colors: Optional[List[str]]
    accent_color: Optional[str]
    heading_font: Optional[str]
    body_font: Optional[str]
    logo_url: Optional[str]
    visual_style: Optional[str]
    usps: Optional[List[str]]
    pain_points_addressed: Optional[List[str]]
    key_messages: Optional[List[str]]
    competitors: Optional[List[str]]
    differentiators: Optional[List[str]]
    enriched_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EnrichmentSuggestion(BaseModel):
    field: str
    current_value: Any
    suggested_value: Any
    reasoning: str


class EnrichmentResponse(BaseModel):
    suggestions: List[EnrichmentSuggestion]
    summary: str


# ── ICP Persona ───────────────────────────────────────────────────────────────

class PersonaCreate(BaseModel):
    persona_name: str
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    gender_skew: Optional[str] = None
    income_bracket: Optional[str] = None
    location_type: Optional[str] = None
    interests: Optional[List[str]] = None
    values: Optional[List[str]] = None
    pain_points: Optional[List[str]] = None
    goals: Optional[List[str]] = None
    preferred_channels: Optional[List[str]] = None
    seo_keywords: Optional[List[str]] = None
    vocabulary: Optional[List[str]] = None
    order: int = 1


class PersonaUpdate(BaseModel):
    persona_name: Optional[str] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    gender_skew: Optional[str] = None
    income_bracket: Optional[str] = None
    location_type: Optional[str] = None
    interests: Optional[List[str]] = None
    values: Optional[List[str]] = None
    pain_points: Optional[List[str]] = None
    goals: Optional[List[str]] = None
    preferred_channels: Optional[List[str]] = None
    seo_keywords: Optional[List[str]] = None
    vocabulary: Optional[List[str]] = None
    order: Optional[int] = None


class PersonaResponse(BaseModel):
    id: int
    client_id: UUID
    persona_name: str
    age_min: Optional[int]
    age_max: Optional[int]
    gender_skew: Optional[str]
    income_bracket: Optional[str]
    location_type: Optional[str]
    interests: Optional[List[str]]
    values: Optional[List[str]]
    pain_points: Optional[List[str]]
    goals: Optional[List[str]]
    preferred_channels: Optional[List[str]]
    seo_keywords: Optional[List[str]]
    vocabulary: Optional[List[str]]
    order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Internal / Brand Context ──────────────────────────────────────────────────

class PersonaContext(BaseModel):
    persona_name: str
    age_range: Optional[str]
    pain_points: Optional[List[str]]
    goals: Optional[List[str]]
    seo_keywords: Optional[List[str]]
    vocabulary: Optional[List[str]]
    preferred_channels: Optional[List[str]]


class BrandContext(BaseModel):
    client_id: UUID
    client_name: str
    industry: Optional[str]
    brand_dna: Optional[BrandDNAResponse]
    personas: List[PersonaContext]
    prompt_block: str   # pre-formatted block for direct Claude injection


# ── Director Suggestions ──────────────────────────────────────────────────────

class Suggestion(BaseModel):
    id: str
    priority: int           # 1=critical 2=high 3=medium 4=low
    service: str            # campaigns | ads | webdev | brand_dna
    title: str
    description: str
    action_label: str
    action_url: str


class SuggestionsResponse(BaseModel):
    client_id: UUID
    suggestions: List[Suggestion]
