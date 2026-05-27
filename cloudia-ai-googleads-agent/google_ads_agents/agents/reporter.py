"""Reporter agent — generates weekly performance reports per client.

Scheduled: Monday 08:00 SAST.

Flow:
1. Pull 7-day campaign metrics via CAMPAIGN_PERFORMANCE_7D
2. Pull 30-day campaign metrics via CAMPAIGN_PERFORMANCE_30D
3. Build rich client context via build_client_context()
4. Send both metric sets + context to Claude → structured JSON report
5. Format into HTML email and deliver to account.report_email
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

import config
from agents.base import AgentRunResult, BaseAgent
from ai.claude import ClaudeClient
from ai.context_builder import build_client_context
from ai.prompts.reporter import REPORTER_SYSTEM_PROMPT
from db.models import Account, IndustryBenchmark
from google_ads.client import AdsClient
from google_ads.queries import CAMPAIGN_PERFORMANCE_7D, CAMPAIGN_PERFORMANCE_30D
from notifications.email import send_weekly_report

logger = logging.getLogger(__name__)

# Micros → ZAR divisor (matches config.MICROS_DIVISOR)
_MICROS_TO_ZAR: int = 1_000_000


class ReporterAgent(BaseAgent):
    """Generates a structured weekly performance report for each active account.

    Compares 7-day and 30-day campaign metrics, interprets them against the
    client's own baselines and KPI targets, and emails a human-readable HTML
    report to the account's report_email address.

    If report_email is not set the report is generated and logged but not sent.
    """

    name = "reporter"

    def execute(self, account: Account) -> AgentRunResult:
        """Run the full report pipeline for one account.

        Args:
            account: The Account ORM row for the client being reported on.

        Returns:
            AgentRunResult summarising the outcome of this execution.
        """
        logger.info("[reporter] Starting weekly report for %s", account.client_name)

        # ── 1. Pull 7-day metrics ──────────────────────────────────────────────
        rows_7d = self.ads.run_query(account.customer_id, CAMPAIGN_PERFORMANCE_7D)
        if not rows_7d:
            logger.warning(
                "[reporter] No 7-day campaign data for %s — skipping report",
                account.client_name,
            )
            return AgentRunResult(
                agent_name=self.name,
                account_id=account.id,
                status="success",
                summary="No campaign data returned for the 7-day window — report skipped",
            )

        campaigns_7d = [_parse_campaign_row_7d(r) for r in rows_7d]
        logger.debug(
            "[reporter] Parsed %d campaigns from 7-day window for %s",
            len(campaigns_7d),
            account.client_name,
        )

        # ── 2. Pull 30-day metrics ─────────────────────────────────────────────
        rows_30d = self.ads.run_query(account.customer_id, CAMPAIGN_PERFORMANCE_30D)
        campaigns_30d = [_parse_campaign_row_30d(r) for r in rows_30d]
        logger.debug(
            "[reporter] Parsed %d campaigns from 30-day window for %s",
            len(campaigns_30d),
            account.client_name,
        )

        # ── 3. Build client context ────────────────────────────────────────────
        benchmarks = self._get_benchmarks(account.industry)
        context = build_client_context(account, benchmarks)

        # ── 4. Send to Claude → structured report JSON ─────────────────────────
        report, tokens_used = self._generate_report(
            context=context,
            campaigns_7d=campaigns_7d,
            campaigns_30d=campaigns_30d,
            account=account,
        )

        # ── 5. Email the report ────────────────────────────────────────────────
        email_sent = False
        if account.report_email:
            email_sent = send_weekly_report(
                account_name=account.client_name,
                report=report,
                report_email=account.report_email,
            )
            if email_sent:
                logger.info(
                    "[reporter] Report emailed to %s for %s",
                    account.report_email,
                    account.client_name,
                )
            else:
                logger.warning(
                    "[reporter] Email delivery failed for %s — report was generated",
                    account.client_name,
                )
        else:
            logger.warning(
                "[reporter] No report_email set for %s — report generated but not sent",
                account.client_name,
            )

        summary = (
            f"Weekly report generated for {account.client_name} "
            f"({len(campaigns_7d)} campaigns / 7d, {len(campaigns_30d)} campaigns / 30d). "
            f"Email {'sent' if email_sent else 'not sent (no address or delivery failure)'}."
        )

        return AgentRunResult(
            agent_name=self.name,
            account_id=account.id,
            status="success",
            tokens_used=tokens_used,
            cost_usd=self.claude.estimate_cost_usd(tokens_used),
            summary=summary,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _generate_report(
        self,
        context: str,
        campaigns_7d: list[dict[str, Any]],
        campaigns_30d: list[dict[str, Any]],
        account: Account,
    ) -> tuple[dict[str, Any], int]:
        """Compose the Claude user message and return the parsed report dict.

        Args:
            context: Pre-built client context string from build_client_context().
            campaigns_7d: List of campaign metric dicts for the 7-day window.
            campaigns_30d: List of campaign metric dicts for the 30-day window.
            account: The Account ORM row (used for report date context).

        Returns:
            Tuple of (report_dict, total_tokens_used).

        Raises:
            ValueError: If Claude returns a response that cannot be parsed as JSON.
        """
        report_date = datetime.now(timezone.utc).strftime("%A, %d %B %Y")

        user_message = _build_report_user_message(
            context=context,
            campaigns_7d=campaigns_7d,
            campaigns_30d=campaigns_30d,
            report_date=report_date,
        )

        logger.debug(
            "[reporter] Calling Claude for %s (7d campaigns: %d, 30d campaigns: %d)",
            account.client_name,
            len(campaigns_7d),
            len(campaigns_30d),
        )

        report, tokens = self.claude.complete_json(
            system_prompt=REPORTER_SYSTEM_PROMPT,
            user_message=user_message,
        )

        logger.debug(
            "[reporter] Claude returned report for %s (%d tokens)",
            account.client_name,
            tokens,
        )
        return report, tokens

    def _get_benchmarks(self, industry: str | None) -> IndustryBenchmark | None:
        """Fetch the IndustryBenchmark row matching the account's industry.

        Args:
            industry: The industry string from Account.industry (may be None).

        Returns:
            The matching IndustryBenchmark ORM row, or None if not found.
        """
        if not industry:
            return None
        stmt = select(IndustryBenchmark).where(IndustryBenchmark.industry == industry)
        return self.db.scalars(stmt).first()


# ── GAQL row parsers ───────────────────────────────────────────────────────────

def _parse_campaign_row_7d(row: Any) -> dict[str, Any]:
    """Parse a CAMPAIGN_PERFORMANCE_7D proto-plus row into a plain dict.

    Monetary values expressed in ZAR (converted from micros) so Claude works
    with human-readable numbers rather than raw API micros values.

    Args:
        row: A GoogleAdsRow proto-plus object returned by AdsClient.run_query().

    Returns:
        A flat dict with all fields needed for the weekly report.
    """
    cost_micros: int = row.metrics.cost_micros or 0
    avg_cpc_micros: int = row.metrics.average_cpc or 0
    cost_per_conv_micros: float = float(row.metrics.cost_per_conversion or 0)

    return {
        "campaign_id": str(row.campaign.id),
        "campaign_name": row.campaign.name,
        "impressions": row.metrics.impressions,
        "clicks": row.metrics.clicks,
        "cost_micros": cost_micros,
        "cost_zar": round(cost_micros / _MICROS_TO_ZAR, 2),
        "conversions": float(row.metrics.conversions or 0),
        "ctr": float(row.metrics.ctr or 0),
        "avg_cpc_micros": avg_cpc_micros,
        "avg_cpc_zar": round(avg_cpc_micros / _MICROS_TO_ZAR, 2),
        "cost_per_conversion": round(cost_per_conv_micros / _MICROS_TO_ZAR, 2),
        "roas": None,  # not in 7D query — sourced from 30D
    }


def _parse_campaign_row_30d(row: Any) -> dict[str, Any]:
    """Parse a CAMPAIGN_PERFORMANCE_30D proto-plus row into a plain dict.

    Monetary values expressed in ZAR (converted from micros).

    Args:
        row: A GoogleAdsRow proto-plus object returned by AdsClient.run_query().

    Returns:
        A flat dict with all fields needed for the 30-day context in the report.
    """
    cost_micros: int = row.metrics.cost_micros or 0
    avg_cpc_micros: int = row.metrics.average_cpc or 0
    cost_per_conv_micros: float = float(row.metrics.cost_per_conversion or 0)
    roas: float = float(row.metrics.roas or 0)

    return {
        "campaign_id": str(row.campaign.id),
        "campaign_name": row.campaign.name,
        "impressions": row.metrics.impressions,
        "clicks": row.metrics.clicks,
        "cost_micros": cost_micros,
        "cost_zar": round(cost_micros / _MICROS_TO_ZAR, 2),
        "conversions": float(row.metrics.conversions or 0),
        "ctr": float(row.metrics.ctr or 0),
        "avg_cpc_micros": avg_cpc_micros,
        "avg_cpc_zar": round(avg_cpc_micros / _MICROS_TO_ZAR, 2),
        "cost_per_conversion": round(cost_per_conv_micros / _MICROS_TO_ZAR, 2),
        "roas": round(roas, 4) if roas else None,
    }


# ── User message builder ───────────────────────────────────────────────────────

def _build_report_user_message(
    context: str,
    campaigns_7d: list[dict[str, Any]],
    campaigns_30d: list[dict[str, Any]],
    report_date: str,
) -> str:
    """Compose the full user message sent to Claude for report generation.

    Args:
        context: Pre-built client context string from build_client_context().
        campaigns_7d: Parsed 7-day campaign metric dicts (cost already in ZAR).
        campaigns_30d: Parsed 30-day campaign metric dicts (cost already in ZAR).
        report_date: Human-readable date string for the report header.

    Returns:
        A structured multi-section string ready to send as the Claude user turn.
    """
    def _format_campaign_table(campaigns: list[dict[str, Any]]) -> str:
        """Render a list of campaign dicts as a human-readable text table."""
        if not campaigns:
            return "  (no data)"
        lines: list[str] = []
        for c in campaigns:
            roas_str = f"{c['roas']:.4f}" if c.get("roas") is not None else "n/a"
            lines.append(
                f"  Campaign: {c['campaign_name']} (ID: {c['campaign_id']})\n"
                f"    Impressions:          {c['impressions']:,}\n"
                f"    Clicks:               {c['clicks']:,}\n"
                f"    CTR:                  {c['ctr']:.4%}\n"
                f"    Cost (ZAR):           R{c['cost_zar']:,.2f}\n"
                f"    Avg CPC (ZAR):        R{c['avg_cpc_zar']:,.2f}\n"
                f"    Conversions:          {c['conversions']:.2f}\n"
                f"    Cost/Conversion (ZAR): R{c['cost_per_conversion']:,.2f}\n"
                f"    ROAS:                 {roas_str}"
            )
        return "\n\n".join(lines)

    return f"""
{context}

=== WEEKLY REPORT DATE ===
{report_date}

=== LAST 7 DAYS — CAMPAIGN METRICS ===
All monetary values in South African Rand (ZAR).

{_format_campaign_table(campaigns_7d)}

=== LAST 30 DAYS — CAMPAIGN METRICS ===
All monetary values in South African Rand (ZAR).

{_format_campaign_table(campaigns_30d)}

=== INSTRUCTIONS ===
Using the client context, baselines, and both metric windows above, generate
the weekly performance report JSON. Be specific about this client's KPIs and
targets. All currency references must be in ZAR. Return ONLY the JSON object.
""".strip()
