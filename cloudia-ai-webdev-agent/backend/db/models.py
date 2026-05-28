"""
SQLAlchemy 2.0 declarative models for the CloudIA website-building agent system.

All JSON columns use sqlalchemy.JSON (not JSONB) for portability with SQLite in tests.
PlatformCredential stores sensitive tokens encrypted at rest via Fernet symmetric
encryption; access is transparently handled by property accessors.
"""

from __future__ import annotations

import datetime
from typing import Any, Optional

from cryptography.fernet import Fernet
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Status constants — match spec exactly
# ---------------------------------------------------------------------------

class ProjectStatus:
    PLANNED = "planned"
    RUNNING = "running"
    AWAITING_CONTENT_REVIEW = "awaiting_content_review"
    AWAITING_SITE_REVIEW = "awaiting_site_review"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    NEEDS_INPUT = "needs_input"

    STATUS_CHOICES: list[str] = [
        PLANNED, RUNNING, AWAITING_CONTENT_REVIEW, AWAITING_SITE_REVIEW,
        COMPLETED, FAILED, CANCELLED, NEEDS_INPUT,
    ]


class AgentTaskStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"

    STATUS_CHOICES: list[str] = [PENDING, RUNNING, COMPLETED, FAILED, SKIPPED, BLOCKED]


class ApprovalGateStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"

    STATUS_CHOICES: list[str] = [PENDING, APPROVED, REJECTED, REVISION_REQUESTED]


class ContentStatus:
    DRAFT = "draft"
    APPROVED = "approved"
    REVISION_REQUESTED = "revision_requested"
    PUBLISHED = "published"

    STATUS_CHOICES: list[str] = [DRAFT, APPROVED, REVISION_REQUESTED, PUBLISHED]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime.datetime:
    return datetime.datetime.utcnow()


def _get_fernet() -> Fernet:
    """Return a Fernet instance using the configured encryption key.
    Import deferred to avoid circular import (models → config → models).
    """
    from backend.config import settings  # noqa: PLC0415
    return Fernet(settings.encryption_key.encode())


# ---------------------------------------------------------------------------
# 1. Client
# ---------------------------------------------------------------------------

class Client(Base):
    """A business client that has engaged CloudIA to build their website."""

    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    business_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    target_audience: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    usp: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tone_of_voice: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    brand_colours: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    brand_fonts: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="South Africa")
    website_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    social_links: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, server_default=func.now()
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    brand_dna_client_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Relationships
    projects: Mapped[list["Project"]] = relationship(
        "Project", back_populates="client", lazy="select"
    )
    platform_credentials: Mapped[list["PlatformCredential"]] = relationship(
        "PlatformCredential",
        back_populates="client",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Client id={self.id} name={self.name!r}>"


# ---------------------------------------------------------------------------
# 2. Project
# ---------------------------------------------------------------------------

class Project(Base):
    """A website-building project for a specific client."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.id"), nullable=False, index=True
    )
    platform: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=ProjectStatus.PLANNED, index=True
    )
    brief: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    pipeline_plan: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    site_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    admin_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    credentials: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    estimated_pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actual_pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    operator_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="projects")
    agent_tasks: Mapped[list["AgentTask"]] = relationship(
        "AgentTask",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="AgentTask.pipeline_order",
    )
    approval_gates: Mapped[list["ApprovalGate"]] = relationship(
        "ApprovalGate",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="ApprovalGate.pipeline_order",
    )
    generated_content: Mapped[list["GeneratedContent"]] = relationship(
        "GeneratedContent",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="select",
    )
    project_media: Mapped[list["ProjectMedia"]] = relationship(
        "ProjectMedia",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} platform={self.platform!r} status={self.status!r}>"


# ---------------------------------------------------------------------------
# 3. AgentTask
# ---------------------------------------------------------------------------

class AgentTask(Base):
    """A discrete pipeline step executed by one of the AI agents."""

    __tablename__ = "agent_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    pipeline_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AgentTaskStatus.PENDING, index=True
    )
    input_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    output_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Optional[float]] = mapped_column(Numeric(8, 6), nullable=True)
    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Relationship
    project: Mapped["Project"] = relationship("Project", back_populates="agent_tasks")

    def __repr__(self) -> str:
        return (
            f"<AgentTask id={self.id} agent={self.agent_name!r} "
            f"order={self.pipeline_order} status={self.status!r}>"
        )


# ---------------------------------------------------------------------------
# 4. ApprovalGate
# ---------------------------------------------------------------------------

class ApprovalGate(Base):
    """A human-in-the-loop checkpoint that blocks the pipeline until approved."""

    __tablename__ = "approval_gates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    gate_name: Mapped[str] = mapped_column(String(100), nullable=False)
    pipeline_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ApprovalGateStatus.PENDING, index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, server_default=func.now()
    )
    reviewed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationship
    project: Mapped["Project"] = relationship("Project", back_populates="approval_gates")

    def __repr__(self) -> str:
        return (
            f"<ApprovalGate id={self.id} gate={self.gate_name!r} status={self.status!r}>"
        )


# ---------------------------------------------------------------------------
# 5. GeneratedContent
# ---------------------------------------------------------------------------

class GeneratedContent(Base):
    """AI-generated copy for a specific page or product."""

    __tablename__ = "generated_content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_slug: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    h1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    body_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cta_text: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    meta_title: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    schema_markup: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ContentStatus.DRAFT
    )
    revision_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    platform_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationship
    project: Mapped["Project"] = relationship("Project", back_populates="generated_content")

    def __repr__(self) -> str:
        return (
            f"<GeneratedContent id={self.id} slug={self.page_slug!r} "
            f"type={self.content_type!r} status={self.status!r}>"
        )


# ---------------------------------------------------------------------------
# 6. ProjectMedia
# ---------------------------------------------------------------------------

class ProjectMedia(Base):
    """An image or media asset sourced for a project page."""

    __tablename__ = "project_media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_slug: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    image_purpose: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    local_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    optimised_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    alt_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attribution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    platform_media_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationship
    project: Mapped["Project"] = relationship("Project", back_populates="project_media")

    def __repr__(self) -> str:
        return (
            f"<ProjectMedia id={self.id} slug={self.page_slug!r} "
            f"purpose={self.image_purpose!r} source={self.source!r}>"
        )


# ---------------------------------------------------------------------------
# 7. PlatformCredential
# ---------------------------------------------------------------------------

class PlatformCredential(Base):
    """
    Encrypted platform credentials for a client's WordPress or Shopify site.

    Sensitive fields (access_token, app_password) are stored encrypted at rest
    using Fernet symmetric encryption. Access is via Python property accessors
    that transparently encrypt on write and decrypt on read.
    """

    __tablename__ = "platform_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    site_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    api_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    shop_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    api_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="2024-01")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow, server_default=func.now()
    )
    last_verified_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)

    # Encrypted columns — raw storage via private mapped attributes
    _access_token_encrypted: Mapped[Optional[str]] = mapped_column(
        "access_token_encrypted", String(2048), nullable=True
    )
    _app_password_encrypted: Mapped[Optional[str]] = mapped_column(
        "app_password_encrypted", String(2048), nullable=True
    )

    # Relationship
    client: Mapped["Client"] = relationship("Client", back_populates="platform_credentials")

    # ------------------------------------------------------------------
    # Transparent encryption/decryption properties
    # ------------------------------------------------------------------

    @property
    def access_token(self) -> Optional[str]:
        """Return the decrypted Shopify access token, or None if not set."""
        if self._access_token_encrypted is None:
            return None
        raw = self._access_token_encrypted
        data: bytes = raw.encode() if isinstance(raw, str) else raw
        return _get_fernet().decrypt(data).decode()

    @access_token.setter
    def access_token(self, value: Optional[str]) -> None:
        if value is None:
            self._access_token_encrypted = None
        else:
            self._access_token_encrypted = _get_fernet().encrypt(value.encode()).decode()

    @property
    def app_password(self) -> Optional[str]:
        """Return the decrypted WordPress application password, or None if not set."""
        if self._app_password_encrypted is None:
            return None
        raw = self._app_password_encrypted
        data: bytes = raw.encode() if isinstance(raw, str) else raw
        return _get_fernet().decrypt(data).decode()

    @app_password.setter
    def app_password(self, value: Optional[str]) -> None:
        if value is None:
            self._app_password_encrypted = None
        else:
            self._app_password_encrypted = _get_fernet().encrypt(value.encode()).decode()

    def __repr__(self) -> str:
        return (
            f"<PlatformCredential id={self.id} platform={self.platform!r} "
            f"site_url={self.site_url!r}>"
        )
