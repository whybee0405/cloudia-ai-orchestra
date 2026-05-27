"""Initial schema — all five tables.

Revision ID: 0001
Revises:
Create Date: 2026-05-24 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_name", sa.String(255), nullable=False),
        sa.Column("customer_id", sa.String(50), nullable=False),
        sa.Column("mcc_id", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), server_default="calibrating", nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("business_type", sa.String(50), nullable=True),
        sa.Column("geo_focus", sa.String(20), nullable=True),
        sa.Column("avg_transaction_value", sa.Numeric(10, 2), nullable=True),
        sa.Column("sales_cycle_days", sa.Integer(), nullable=True),
        sa.Column("primary_kpi", sa.String(20), nullable=True),
        sa.Column("primary_kpi_target", sa.Numeric(10, 2), nullable=True),
        sa.Column("secondary_kpi", sa.String(20), nullable=True),
        sa.Column("secondary_kpi_target", sa.Numeric(10, 2), nullable=True),
        sa.Column("monthly_ad_spend", sa.Numeric(10, 2), nullable=True),
        sa.Column("budget_sensitivity", sa.String(20), nullable=True),
        sa.Column("min_daily_budget", sa.Numeric(10, 2), nullable=True),
        sa.Column("baseline_ctr", sa.Numeric(6, 4), nullable=True),
        sa.Column("baseline_cvr", sa.Numeric(6, 4), nullable=True),
        sa.Column("baseline_cpc", sa.Numeric(10, 2), nullable=True),
        sa.Column("baseline_cpa", sa.Numeric(10, 2), nullable=True),
        sa.Column("baseline_roas", sa.Numeric(8, 2), nullable=True),
        sa.Column("baseline_set_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("peak_months", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("slow_months", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("custom_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("alert_email", sa.String(255), nullable=True),
        sa.Column("report_email", sa.String(255), nullable=True),
        sa.Column("onboarded_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_id"),
    )

    op.create_table(
        "industry_benchmarks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("industry", sa.String(100), nullable=False),
        sa.Column("avg_ctr", sa.Numeric(6, 4), nullable=True),
        sa.Column("avg_cvr", sa.Numeric(6, 4), nullable=True),
        sa.Column("avg_cpc_zar", sa.Numeric(10, 2), nullable=True),
        sa.Column("avg_cpa_zar", sa.Numeric(10, 2), nullable=True),
        sa.Column("good_quality_score", sa.Integer(), server_default="7", nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "campaign_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.String(50), nullable=False),
        sa.Column("campaign_name", sa.String(255), nullable=True),
        sa.Column("snapshot_time", sa.TIMESTAMP(), nullable=False),
        sa.Column("impressions", sa.BigInteger(), nullable=True),
        sa.Column("clicks", sa.BigInteger(), nullable=True),
        sa.Column("cost_micros", sa.BigInteger(), nullable=True),
        sa.Column("conversions", sa.Numeric(10, 2), nullable=True),
        sa.Column("ctr", sa.Numeric(6, 4), nullable=True),
        sa.Column("avg_cpc_micros", sa.BigInteger(), nullable=True),
        sa.Column("conversion_rate", sa.Numeric(6, 4), nullable=True),
        sa.Column("cost_per_conversion", sa.Numeric(10, 2), nullable=True),
        sa.Column("roas", sa.Numeric(8, 2), nullable=True),
        sa.Column("budget_micros", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("run_time", sa.TIMESTAMP(), nullable=False),
        sa.Column("campaign_id", sa.String(50), nullable=True),
        sa.Column("anomaly_type", sa.String(100), nullable=True),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("delta_value", sa.Numeric(10, 4), nullable=True),
        sa.Column("threshold_used", sa.Numeric(10, 4), nullable=True),
        sa.Column("acknowledged", sa.Boolean(), server_default="false", nullable=True),
        sa.Column("acknowledged_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("acknowledged_by", sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "approval_queue",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("agent_name", sa.String(50), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=True),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("action_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending", nullable=True),
        sa.Column("reviewed_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("reviewed_by", sa.String(100), nullable=True),
        sa.Column("executed_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("execution_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("agent_name", sa.String(50), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(8, 6), nullable=True),
        sa.Column("decisions_generated", sa.Integer(), nullable=True),
        sa.Column("anomalies_found", sa.Integer(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Useful indexes
    op.create_index("ix_campaign_snapshots_account_campaign", "campaign_snapshots", ["account_id", "campaign_id"])
    op.create_index("ix_campaign_snapshots_time", "campaign_snapshots", ["snapshot_time"])
    op.create_index("ix_audit_log_account_severity", "audit_log", ["account_id", "severity"])
    op.create_index("ix_approval_queue_status", "approval_queue", ["status"])
    op.create_index("ix_agent_runs_account", "agent_runs", ["account_id"])


def downgrade() -> None:
    op.drop_table("agent_runs")
    op.drop_table("approval_queue")
    op.drop_table("audit_log")
    op.drop_table("campaign_snapshots")
    op.drop_table("industry_benchmarks")
    op.drop_table("accounts")
