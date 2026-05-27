"""
Pydantic v2 request/response schemas for the CloudIA Website Agents API.

These schemas are used by FastAPI for request validation, serialisation,
and OpenAPI documentation generation. All models use ``from_attributes=True``
where SQLAlchemy ORM objects are returned directly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------


class ClientCreate(BaseModel):
    name: str
    industry: Optional[str] = None
    business_type: Optional[str] = None
    target_audience: Optional[str] = None
    usp: Optional[str] = None
    tone_of_voice: Optional[str] = "professional"
    brand_colours: Optional[dict] = None
    brand_fonts: Optional[dict] = None
    logo_url: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: str = "South Africa"
    website_url: Optional[str] = None
    social_links: Optional[dict] = None
    notes: Optional[str] = None


class ClientOut(ClientCreate):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


class ProjectCreate(BaseModel):
    client_id: int
    platform: Optional[str] = None  # None → auto-detect from brief
    brief: dict

    @field_validator("platform")
    @classmethod
    def platform_must_be_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("wordpress", "shopify"):
            raise ValueError("platform must be 'wordpress', 'shopify', or null")
        return v


class ProjectOut(BaseModel):
    id: int
    client_id: int
    platform: Optional[str]
    status: str
    brief: Optional[dict]
    pipeline_plan: Optional[dict] = None
    site_url: Optional[str] = None
    estimated_pages: Optional[int] = None
    actual_pages: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    operator_notes: Optional[str] = None
    tasks: list["AgentTaskOut"] = []
    gates: list["ApprovalGateOut"] = []
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Agent Tasks
# ---------------------------------------------------------------------------


class AgentTaskOut(BaseModel):
    id: int
    agent_name: str
    pipeline_order: int = 0
    status: str
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    retry_count: int = 0
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Approval Gates
# ---------------------------------------------------------------------------


class ApprovalGateOut(BaseModel):
    id: int
    gate_name: str
    pipeline_order: int = 0
    status: str
    notes: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    model_config = {"from_attributes": True}


class ApprovalAction(BaseModel):
    notes: Optional[str] = None
    reviewed_by: str = "operator"


class ApprovalReject(BaseModel):
    notes: str = Field(..., min_length=1, description="Notes required on rejection")
    reviewed_by: str = "operator"


# ---------------------------------------------------------------------------
# Generated Content
# ---------------------------------------------------------------------------


class ContentOut(BaseModel):
    id: int
    page_slug: str = ""
    content_type: str
    title: Optional[str] = None
    h1: Optional[str] = None
    body_content: Optional[str] = None
    cta_text: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    status: str = "draft"
    revision_notes: Optional[str] = None
    model_config = {"from_attributes": True}


class ContentUpdate(BaseModel):
    title: Optional[str] = None
    h1: Optional[str] = None
    body_content: Optional[str] = None
    cta_text: Optional[str] = None
    meta_title: Optional[str] = Field(None, max_length=60)
    meta_description: Optional[str] = Field(None, max_length=160)
    revision_notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Platform Credentials
# ---------------------------------------------------------------------------


class CredentialCreate(BaseModel):
    client_id: int
    platform: str
    site_url: str
    api_url: Optional[str] = None
    access_token: Optional[str] = None
    app_password: Optional[str] = None
    shop_name: Optional[str] = None
    api_version: str = "2024-01"

    @field_validator("platform")
    @classmethod
    def platform_must_be_valid(cls, v: str) -> str:
        if v not in ("wordpress", "shopify"):
            raise ValueError("platform must be 'wordpress' or 'shopify'")
        return v


class CredentialOut(BaseModel):
    id: int
    client_id: int
    platform: str
    site_url: str
    shop_name: Optional[str] = None
    is_active: bool = True
    last_verified_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# System status
# ---------------------------------------------------------------------------


class SystemStatus(BaseModel):
    db_connected: bool
    redis_connected: bool
    celery_worker_active: bool


# ---------------------------------------------------------------------------
# Resolve forward references
# ---------------------------------------------------------------------------

ProjectOut.model_rebuild()
