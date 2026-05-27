"""Builds per-client context strings injected into every Claude prompt."""

import json
from datetime import datetime, timezone

from db.models import Account, IndustryBenchmark


def _fmt_zar(value: float | None) -> str:
    """Format a ZAR monetary amount. Returns 'not specified' if None."""
    if value is None:
        return "not specified"
    return f"R{value:,.2f}"


def _fmt_val(value: object) -> str:
    """Format an optional value, returning 'not specified' if None."""
    if value is None:
        return "not specified"
    return str(value)


def build_client_context(account: Account, benchmarks: IndustryBenchmark | None) -> str:
    """Return a rich context string for the given account.

    This is the most important function in the system — every Claude call
    receives this as the first section of its user message.

    Args:
        account: The Account ORM row for the client.
        benchmarks: The matching IndustryBenchmark row (may be None if not found).

    Returns:
        A formatted multi-section context string.
    """
    current_month = datetime.now(timezone.utc).month
    peak_months: list[int] = account.peak_months or []
    slow_months: list[int] = account.slow_months or []

    if current_month in peak_months:
        season_label = "PEAK SEASON"
    elif current_month in slow_months:
        season_label = "SLOW SEASON"
    else:
        season_label = "NORMAL PERIOD"

    benchmark_section = _format_benchmarks(benchmarks, account.industry)

    return f"""
=== CLIENT CONTEXT ===
Client: {account.client_name}
Industry: {_fmt_val(account.industry)}
Business type: {_fmt_val(account.business_type)}
Geographic focus: {_fmt_val(account.geo_focus)}
Average transaction value: {_fmt_zar(account.avg_transaction_value)}
Sales cycle: {_fmt_val(account.sales_cycle_days)} days

=== GOALS ===
Primary KPI: {_fmt_val(account.primary_kpi)} — target: {_fmt_val(account.primary_kpi_target)}
Secondary KPI: {_fmt_val(account.secondary_kpi)} — target: {_fmt_val(account.secondary_kpi_target)}
Monthly ad spend budget: {_fmt_zar(account.monthly_ad_spend)}
Budget sensitivity: {account.budget_sensitivity or 'moderate'}
Minimum daily budget floor: {_fmt_zar(account.min_daily_budget)}

=== CLIENT BASELINE (established over first 30 days) ===
CTR: {_fmt_val(account.baseline_ctr)}
CVR: {_fmt_val(account.baseline_cvr)}
CPC: {_fmt_zar(account.baseline_cpc)}
CPA: {_fmt_zar(account.baseline_cpa)}
ROAS: {_fmt_val(account.baseline_roas)}

{benchmark_section}

=== SEASONALITY ===
Current period: {season_label} (Month {current_month})
Peak months: {peak_months or 'none specified'}
Slow months: {slow_months or 'none specified'}

=== HARD RULES — YOU MUST FOLLOW THESE WITHOUT EXCEPTION ===
{json.dumps(account.custom_rules or {}, indent=2)}

=== YOUR ROLE ===
You are a senior Google Ads strategist operating as part of an automated
management system for CloudIA, a South African digital agency.
All your recommendations must be:
1. Specific to THIS client's industry, goals, and baseline — not generic
2. Proportional to their budget sensitivity level
3. Compliant with every hard rule listed above
4. Expressed in South African Rand (ZAR)
5. Structured as JSON where action output is required
Do not hallucinate metrics. If data is missing, say so.
""".strip()


def _format_benchmarks(benchmarks: IndustryBenchmark | None, industry: str | None) -> str:
    """Format the industry benchmarks section."""
    if benchmarks is None:
        return f"=== INDUSTRY BENCHMARKS ({industry or 'unknown'}) ===\nNo benchmark data available for this industry."

    return f"""=== INDUSTRY BENCHMARKS ({industry or benchmarks.industry}) ===
Average CTR: {benchmarks.avg_ctr or 'n/a'}
Average CVR: {benchmarks.avg_cvr or 'n/a'}
Average CPC: R{benchmarks.avg_cpc_zar or 'n/a'}
Average CPA: R{benchmarks.avg_cpa_zar or 'n/a'}
Good quality score threshold: {benchmarks.good_quality_score}
Source: {benchmarks.source or 'n/a'}"""
