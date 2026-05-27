"""SQLAlchemy ORM models — exact schema from MASTER_PROMPT.md Section 4."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    TIMESTAMP,
)

Timestamp = TIMESTAMP  # alias used throughout this module
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Shared declarative base for all models."""

    pass


class Account(Base):
    """Master client registry. Every other table references this."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    mcc_id: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="calibrating")

    # Business context
    industry: Mapped[str | None] = mapped_column(String(100))
    business_type: Mapped[str | None] = mapped_column(String(50))
    geo_focus: Mapped[str | None] = mapped_column(String(20))
    avg_transaction_value: Mapped[float | None] = mapped_column(Numeric(10, 2))
    sales_cycle_days: Mapped[int | None] = mapped_column(Integer)

    # Goal hierarchy
    primary_kpi: Mapped[str | None] = mapped_column(String(20))
    primary_kpi_target: Mapped[float | None] = mapped_column(Numeric(10, 2))
    secondary_kpi: Mapped[str | None] = mapped_column(String(20))
    secondary_kpi_target: Mapped[float | None] = mapped_column(Numeric(10, 2))

    # Budget context
    monthly_ad_spend: Mapped[float | None] = mapped_column(Numeric(10, 2))
    budget_sensitivity: Mapped[str | None] = mapped_column(String(20))
    min_daily_budget: Mapped[float | None] = mapped_column(Numeric(10, 2))

    # Baselines
    baseline_ctr: Mapped[float | None] = mapped_column(Numeric(6, 4))
    baseline_cvr: Mapped[float | None] = mapped_column(Numeric(6, 4))
    baseline_cpc: Mapped[float | None] = mapped_column(Numeric(10, 2))
    baseline_cpa: Mapped[float | None] = mapped_column(Numeric(10, 2))
    baseline_roas: Mapped[float | None] = mapped_column(Numeric(8, 2))
    baseline_set_at: Mapped[datetime | None] = mapped_column(Timestamp)

    # Seasonality
    peak_months: Mapped[list[int] | None] = mapped_column(JSONB)
    slow_months: Mapped[list[int] | None] = mapped_column(JSONB)

    # Rules engine
    custom_rules: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Admin
    alert_email: Mapped[str | None] = mapped_column(String(255))
    report_email: Mapped[str | None] = mapped_column(String(255))
    onboarded_at: Mapped[datetime] = mapped_column(
        Timestamp, server_default=func.now()
    )
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    snapshots: Mapped[list["CampaignSnapshot"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )
    audit_entries: Mapped[list["AuditLog"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )
    queue_items: Mapped[list["ApprovalQueue"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )
    agent_runs: Mapped[list["AgentRun"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Account id={self.id} name={self.client_name!r} status={self.status!r}>"


class CampaignSnapshot(Base):
    """Point-in-time campaign metrics. Auditor diffs these."""

    __tablename__ = "campaign_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(50), nullable=False)
    campaign_name: Mapped[str | None] = mapped_column(String(255))
    snapshot_time: Mapped[datetime] = mapped_column(Timestamp, nullable=False)
    impressions: Mapped[int | None] = mapped_column(BigInteger)
    clicks: Mapped[int | None] = mapped_column(BigInteger)
    cost_micros: Mapped[int | None] = mapped_column(BigInteger)
    conversions: Mapped[float | None] = mapped_column(Numeric(10, 2))
    ctr: Mapped[float | None] = mapped_column(Numeric(6, 4))
    avg_cpc_micros: Mapped[int | None] = mapped_column(BigInteger)
    conversion_rate: Mapped[float | None] = mapped_column(Numeric(6, 4))
    cost_per_conversion: Mapped[float | None] = mapped_column(Numeric(10, 2))
    roas: Mapped[float | None] = mapped_column(Numeric(8, 2))
    budget_micros: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str | None] = mapped_column(String(50))
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    account: Mapped["Account"] = relationship(back_populates="snapshots")

    def __repr__(self) -> str:
        return (
            f"<CampaignSnapshot id={self.id} "
            f"campaign={self.campaign_id!r} "
            f"time={self.snapshot_time}>"
        )


class AuditLog(Base):
    """Every anomaly detected. Persisted even if no action taken."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    run_time: Mapped[datetime] = mapped_column(Timestamp, nullable=False)
    campaign_id: Mapped[str | None] = mapped_column(String(50))
    anomaly_type: Mapped[str | None] = mapped_column(String(100))
    severity: Mapped[str | None] = mapped_column(String(20))
    diagnosis: Mapped[str | None] = mapped_column(Text)
    recommended_action: Mapped[str | None] = mapped_column(Text)
    delta_value: Mapped[float | None] = mapped_column(Numeric(10, 4))
    threshold_used: Mapped[float | None] = mapped_column(Numeric(10, 4))
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(Timestamp)
    acknowledged_by: Mapped[str | None] = mapped_column(String(100))

    account: Mapped["Account"] = relationship(back_populates="audit_entries")

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} "
            f"type={self.anomaly_type!r} "
            f"severity={self.severity!r}>"
        )


class ApprovalQueue(Base):
    """All agent decisions waiting for human review. NOTHING executes without approval."""

    __tablename__ = "approval_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        Timestamp, server_default=func.now()
    )
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    action_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    reasoning: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    reviewed_at: Mapped[datetime | None] = mapped_column(Timestamp)
    reviewed_by: Mapped[str | None] = mapped_column(String(100))
    executed_at: Mapped[datetime | None] = mapped_column(Timestamp)
    execution_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    failure_reason: Mapped[str | None] = mapped_column(Text)

    account: Mapped["Account"] = relationship(back_populates="queue_items")

    def __repr__(self) -> str:
        return (
            f"<ApprovalQueue id={self.id} "
            f"agent={self.agent_name!r} "
            f"action={self.action_type!r} "
            f"status={self.status!r}>"
        )


class IndustryBenchmark(Base):
    """Reference data injected into every prompt alongside client baseline."""

    __tablename__ = "industry_benchmarks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    industry: Mapped[str] = mapped_column(String(100), nullable=False)
    avg_ctr: Mapped[float | None] = mapped_column(Numeric(6, 4))
    avg_cvr: Mapped[float | None] = mapped_column(Numeric(6, 4))
    avg_cpc_zar: Mapped[float | None] = mapped_column(Numeric(10, 2))
    avg_cpa_zar: Mapped[float | None] = mapped_column(Numeric(10, 2))
    good_quality_score: Mapped[int] = mapped_column(Integer, default=7)
    source: Mapped[str | None] = mapped_column(String(100))
    updated_at: Mapped[datetime | None] = mapped_column(Timestamp)
    notes: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<IndustryBenchmark id={self.id} industry={self.industry!r}>"


class AgentRun(Base):
    """Every agent execution logged for debugging and cost tracking."""

    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_name: Mapped[str] = mapped_column(String(50), nullable=False)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))
    started_at: Mapped[datetime | None] = mapped_column(Timestamp)
    completed_at: Mapped[datetime | None] = mapped_column(Timestamp)
    status: Mapped[str | None] = mapped_column(String(20))
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(8, 6))
    decisions_generated: Mapped[int | None] = mapped_column(Integer)
    anomalies_found: Mapped[int | None] = mapped_column(Integer)
    summary: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)

    account: Mapped["Account | None"] = relationship(back_populates="agent_runs")

    def __repr__(self) -> str:
        return (
            f"<AgentRun id={self.id} "
            f"agent={self.agent_name!r} "
            f"status={self.status!r}>"
        )
