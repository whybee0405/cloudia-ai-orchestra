"""Test data factories — produce realistic model dicts for all test scenarios."""

from datetime import datetime, timedelta, timezone
from typing import Any


def make_account(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "client_name": "Test Dental Practice",
        "customer_id": "123-456-7890",
        "mcc_id": "987-654-3210",
        "industry": "dental",
        "business_type": "local_service",
        "geo_focus": "local",
        "avg_transaction_value": 1500.00,
        "sales_cycle_days": 1,
        "monthly_ad_spend": 5000.00,
        "budget_sensitivity": "conservative",
        "min_daily_budget": 100.00,
        "primary_kpi": "CPL",
        "primary_kpi_target": 200.00,
        "secondary_kpi": None,
        "secondary_kpi_target": None,
        "baseline_ctr": 0.045,
        "baseline_cvr": 0.032,
        "baseline_cpc": 12.50,
        "baseline_cpa": 390.00,
        "baseline_roas": None,
        "baseline_set_at": datetime.utcnow() - timedelta(days=45),
        "peak_months": [1, 6],
        "slow_months": [7, 8],
        "custom_rules": {
            "never_pause_brand_campaign": True,
            "max_cpc_increase_pct": 15,
            "competitor_bidding_allowed": False,
        },
        "status": "active",
        "alert_email": "alerts@dental.co.za",
        "report_email": "reports@dental.co.za",
    }
    return {**defaults, **(overrides or {})}


def make_snapshot(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "campaign_id": "111222333",
        "campaign_name": "Brand - Search",
        "impressions": 5000,
        "clicks": 225,
        "cost_micros": 4_500_000_000,
        "conversions": 7.0,
        "ctr": 0.045,
        "avg_cpc_micros": 20_000_000,
        "conversion_rate": 0.031,
        "cost_per_conversion": 642_857_143,
        "roas": None,
        "budget_micros": 500_000_000,
        "status": "ENABLED",
    }
    return {**defaults, **(overrides or {})}


def make_campaign_metrics(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "campaign_id": "111222333",
        "campaign_name": "Brand - Search",
        "status": "ENABLED",
        "budget_micros": 500_000_000,
        "impressions": 5000,
        "clicks": 225,
        "cost_micros": 4_500_000_000,
        "conversions": 7.0,
        "ctr": 0.045,
        "avg_cpc_micros": 20_000_000,
        "cost_per_conversion": 642_857_143,
        "conversion_rate": 0.031,
        "search_impression_share": 0.65,
    }
    return {**defaults, **(overrides or {})}


def make_audit_log_entry(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "account_id": 1,
        "run_time": datetime.now(timezone.utc),
        "campaign_id": "111222333",
        "anomaly_type": "ctr_drop",
        "severity": "MEDIUM",
        "diagnosis": "CTR dropped significantly vs prior period.",
        "recommended_action": "Review ad copy and landing page.",
        "delta_value": -31.5,
        "threshold_used": -30.0,
        "acknowledged": False,
    }
    return {**defaults, **(overrides or {})}


def make_approval_queue_item(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "account_id": 1,
        "agent_name": "manager",
        "action_type": "increase_bid",
        "action_payload": {
            "ad_group_id": "444555666",
            "target_name": "Teeth Whitening - Ad Group",
            "current_value": 15_000_000,
            "recommended_value": 17_000_000,
            "reasoning": "CTR above baseline, CPL on target — increase bid to capture more volume.",
        },
        "reasoning": "CTR above baseline — increase bid to capture more volume.",
        "status": "pending",
    }
    return {**defaults, **(overrides or {})}


def make_benchmarks(industry: str = "dental", overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "industry": industry,
        "avg_ctr": 0.038,
        "avg_cvr": 0.028,
        "avg_cpc_zar": 18.50,
        "avg_cpa_zar": 420.00,
        "good_quality_score": 7,
        "source": "wordstream_2024",
    }
    return {**defaults, **(overrides or {})}
