"""
Test factories for the CloudIA test suite.

All factory functions create and persist records in the provided SQLAlchemy
session and return the refreshed ORM instance. Column names match models.py exactly.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session


def make_client(db: Session, overrides: Optional[dict] = None):
    """Create and persist a Client."""
    from backend.db.models import Client

    defaults: dict[str, Any] = {
        "name": "Sandton Dental Studio",
        "industry": "dental",
        "business_type": "local_service",
        "target_audience": "Adults 30-60 in Sandton seeking cosmetic and general dental care",
        "usp": "Same-day emergency appointments and transparent pricing",
        "tone_of_voice": "professional",
        "brand_colours": {"primary": "#1A3C5E", "secondary": "#C8A96E", "accent": "#FFFFFF"},
        "brand_fonts": {"heading": "Playfair Display", "body": "Inter"},
        "city": "Johannesburg",
        "country": "South Africa",
        "contact_email": "info@sandtondental.co.za",
        "contact_phone": "+27 11 000 0000",
    }
    if overrides:
        defaults.update(overrides)

    instance = Client(**defaults)
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance


def make_project(
    db: Session,
    client_id: int,
    platform: str = "wordpress",
    overrides: Optional[dict] = None,
):
    """Create and persist a Project."""
    from backend.db.models import Project

    defaults: dict[str, Any] = {
        "client_id": client_id,
        "platform": platform,
        "status": "planned",
        "brief": {
            "what_does_business_do": "Dental clinic offering general and cosmetic dentistry",
            "target_customer": "Adults 30-60 in Sandton",
            "usp": "Same-day emergency appointments",
            "cta_goal": "Book an appointment",
            "pages_needed": ["home", "about", "services", "contact"],
        },
        "pipeline_plan": {
            "platform": platform,
            "estimated_pages": 4,
            "page_list": ["home", "about", "services", "contact"],
        },
    }
    if overrides:
        defaults.update(overrides)

    instance = Project(**defaults)
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance


def make_agent_task(
    db: Session,
    project_id: int,
    agent_name: str,
    pipeline_order: int = 1,
    overrides: Optional[dict] = None,
):
    """Create and persist an AgentTask."""
    from backend.db.models import AgentTask

    defaults: dict[str, Any] = {
        "project_id": project_id,
        "agent_name": agent_name,
        "pipeline_order": pipeline_order,
        "status": "pending",
        "retry_count": 0,
    }
    if overrides:
        defaults.update(overrides)

    instance = AgentTask(**defaults)
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance


def make_approval_gate(
    db: Session,
    project_id: int,
    gate_name: str,
    pipeline_order: int = 1,
    overrides: Optional[dict] = None,
):
    """Create and persist an ApprovalGate."""
    from backend.db.models import ApprovalGate

    defaults: dict[str, Any] = {
        "project_id": project_id,
        "gate_name": gate_name,
        "pipeline_order": pipeline_order,
        "status": "pending",
    }
    if overrides:
        defaults.update(overrides)

    instance = ApprovalGate(**defaults)
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance


def make_generated_content(
    db: Session,
    project_id: int,
    page_slug: str,
    overrides: Optional[dict] = None,
):
    """Create and persist a GeneratedContent record."""
    from backend.db.models import GeneratedContent

    defaults: dict[str, Any] = {
        "project_id": project_id,
        "page_slug": page_slug,
        "content_type": "page",
        "title": "Welcome to Sandton Dental Studio",
        "h1": "Expert Dental Care in Sandton",
        "body_content": (
            "We provide comprehensive dental services for adults and families in "
            "Sandton. Our team of experienced dentists is committed to your oral health "
            "and offers same-day emergency appointments."
        ),
        "cta_text": "Book Your Appointment Today",
        "meta_title": "Sandton Dental — Cosmetic Dentistry",
        "meta_description": (
            "Expert dental care in Sandton. Same-day emergency appointments. "
            "Transparent pricing. Book online today."
        ),
        "status": "draft",
    }
    if overrides:
        defaults.update(overrides)

    instance = GeneratedContent(**defaults)
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance


def make_credentials(
    db: Session,
    client_id: int,
    platform: str = "wordpress",
    overrides: Optional[dict] = None,
):
    """Create and persist a PlatformCredential with encrypted secrets."""
    from backend.db.models import PlatformCredential

    defaults: dict[str, Any] = {
        "client_id": client_id,
        "platform": platform,
        "site_url": "https://test.sandtondental.co.za",
        "is_active": True,
    }
    if overrides:
        defaults.update(overrides)

    instance = PlatformCredential(**defaults)

    if platform == "wordpress":
        instance.app_password = "test_app_password_123"
    else:
        instance.access_token = "shpat_test_access_token_123"

    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance
