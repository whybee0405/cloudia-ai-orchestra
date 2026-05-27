"""Manager agent — daily bid and budget optimisation recommendations.

Scheduled: daily at 10:00 SAST.

Flow:
1. Pull 7-day campaign metrics via CAMPAIGN_PERFORMANCE_7D
2. Pull ad group bids via ADGROUP_BIDS
3. Build rich client context via build_client_context()
4. Send all data to Claude with MANAGER_SYSTEM_PROMPT → returns JSON decisions
5. Validate each decision against account.custom_rules (hard-rule enforcement)
6. Write every valid decision to approval_queue with status='pending'
7. Email an action-required summary to account.alert_email

Nothing executes against the Google Ads API here — the manager only queues
decisions for human review.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

import config
from agents.base import AgentRunResult, BaseAgent
from ai.claude import ClaudeClient
from ai.context_builder import build_client_context
from ai.prompts.manager import MANAGER_SYSTEM_PROMPT
from db.models import Account, ApprovalQueue, IndustryBenchmark
from db.queue import write_queue_item
from google_ads.client import AdsClient
from google_ads.queries import ADGROUP_BIDS, CAMPAIGN_PERFORMANCE_7D
from notifications.email import send_queue_summary

logger = logging.getLogger(__name__)


class ManagerAgent(BaseAgent):
    """Generates daily bid and budget optimisation decisions for one account.

    The agent pulls 7-day campaign and ad group data, asks Claude to reason
    over the metrics against the client's goals and baselines, and then
    validates each recommendation against the account's custom_rules before
    writing it to the approval queue.

    All decisions land with status='pending'. Nothing executes until a human
    approves via the dashboard.
    """

    name = "manager"

    def execute(self, account: Account) -> AgentRunResult:
        """Run the manager optimisation pipeline for one account.

        Args:
            account: The Account ORM row for the client being optimised.

        Returns:
            AgentRunResult with decisions_generated set to the number of valid
            decisions written to the approval queue.
        """
        logger.info("[manager] Starting for %s", account.client_name)

        # ── 1. Pull 7-day campaign metrics ────────────────────────────────────
        campaign_rows = self.ads.run_query(account.customer_id, CAMPAIGN_PERFORMANCE_7D)
        if not campaign_rows:
            logger.warning(
                "[manager] No campaign data returned for %s — skipping",
                account.client_name,
            )
            return AgentRunResult(
                agent_name=self.name,
                account_id=account.id,
                status="success",
                summary="No campaign data returned from API — manager skipped",
            )

        campaigns = [_parse_campaign_row(r) for r in campaign_rows]
        logger.debug(
            "[manager] Parsed %d campaign rows for %s",
            len(campaigns),
            account.client_name,
        )

        # ── 2. Pull ad group bids ─────────────────────────────────────────────
        adgroup_rows = self.ads.run_query(account.customer_id, ADGROUP_BIDS)
        adgroups = [_parse_adgroup_row(r) for r in adgroup_rows]
        logger.debug(
            "[manager] Parsed %d ad group rows for %s",
            len(adgroups),
            account.client_name,
        )

        # ── 3. Build client context ───────────────────────────────────────────
        benchmarks = self._get_benchmarks(account.industry)
        context = build_client_context(account, benchmarks)

        # ── 4. Send to Claude → structured decision JSON ──────────────────────
        raw_decisions, tokens_used = self._generate_decisions(
            context=context,
            campaigns=campaigns,
            adgroups=adgroups,
            account=account,
        )

        # ── 5. Validate decisions against account.custom_rules ────────────────
        custom_rules: dict[str, Any] = account.custom_rules or {}
        valid_decisions: list[dict[str, Any]] = []
        skipped = 0

        for decision in raw_decisions:
            payload_error = _validate_decision_payload(decision)
            if payload_error:
                logger.info(
                    "[manager] Skipping decision '%s' for target '%s' — invalid payload: %s",
                    decision.get("action_type"),
                    decision.get("target_name"),
                    payload_error,
                )
                skipped += 1
                continue

            blocked_by = _check_custom_rules(decision, custom_rules)
            if blocked_by:
                logger.info(
                    "[manager] Skipping decision '%s' for target '%s' — blocked by rule: %s",
                    decision.get("action_type"),
                    decision.get("target_name"),
                    blocked_by,
                )
                skipped += 1
            else:
                valid_decisions.append(decision)

        logger.info(
            "[manager] %d decisions valid, %d skipped by custom_rules for %s",
            len(valid_decisions),
            skipped,
            account.client_name,
        )

        # ── 6. Write valid decisions to approval_queue ────────────────────────
        for decision in valid_decisions:
            write_queue_item(
                db=self.db,
                account_id=account.id,
                agent_name=self.name,
                action_type=decision.get("action_type", "unknown"),
                action_payload=decision,
                reasoning=decision.get("reasoning", ""),
            )

        # ── 7. Email summary to account.alert_email ───────────────────────────
        if valid_decisions and account.alert_email:
            send_queue_summary(
                account_name=account.client_name,
                decisions=valid_decisions,
                alert_email=account.alert_email,
            )
        elif not account.alert_email and valid_decisions:
            logger.warning(
                "[manager] No alert_email configured for %s — skipping summary email",
                account.client_name,
            )

        summary = (
            f"Manager completed for {account.client_name}: "
            f"{len(campaigns)} campaigns, {len(adgroups)} ad groups analysed, "
            f"{len(valid_decisions)} decisions queued"
            + (f", {skipped} skipped by custom_rules" if skipped else "")
            + "."
        )

        return AgentRunResult(
            agent_name=self.name,
            account_id=account.id,
            status="success",
            tokens_used=tokens_used,
            cost_usd=self.claude.estimate_cost_usd(tokens_used),
            decisions_generated=len(valid_decisions),
            summary=summary,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _generate_decisions(
        self,
        context: str,
        campaigns: list[dict[str, Any]],
        adgroups: list[dict[str, Any]],
        account: Account,
    ) -> tuple[list[dict[str, Any]], int]:
        """Build the Claude user message and return the parsed decision list.

        Args:
            context: Pre-built client context string from build_client_context().
            campaigns: Parsed campaign metric dicts from CAMPAIGN_PERFORMANCE_7D.
            adgroups: Parsed ad group bid dicts from ADGROUP_BIDS.
            account: The Account ORM row (used for logging only).

        Returns:
            Tuple of (list_of_decision_dicts, total_tokens_used).

        Raises:
            ValueError: If Claude returns a response that cannot be parsed as JSON.
        """
        user_message = _build_manager_user_message(
            context=context,
            campaigns=campaigns,
            adgroups=adgroups,
        )

        logger.debug(
            "[manager] Calling Claude for %s (%d campaigns, %d ad groups)",
            account.client_name,
            len(campaigns),
            len(adgroups),
        )

        result, tokens = self.claude.complete_json(
            system_prompt=MANAGER_SYSTEM_PROMPT,
            user_message=user_message,
        )

        decisions: list[dict[str, Any]] = result.get("decisions", [])
        logger.debug(
            "[manager] Claude returned %d decisions for %s (%d tokens)",
            len(decisions),
            account.client_name,
            tokens,
        )
        return decisions, tokens

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


# ── Custom rules validation ────────────────────────────────────────────────────

def _check_custom_rules(
    decision: dict[str, Any],
    custom_rules: dict[str, Any],
) -> str | None:
    """Validate a single decision against the account's custom_rules dict.

    Checks are applied in order. The first violated rule short-circuits and
    returns the name of the blocking rule so it can be logged.

    Supported rules:
        never_pause_brand_campaign (bool):
            When True, any 'pause_campaign' decision is blocked.

        max_cpc_increase_pct (float):
            Maximum allowed percentage increase for 'increase_bid' decisions.
            Calculated as (recommended - current) / current * 100.

        max_daily_spend_increase_pct (float):
            Maximum allowed percentage increase for 'increase_budget' decisions.
            Calculated as (recommended - current) / current * 100.

    Args:
        decision: A single decision dict as returned by Claude.
        custom_rules: The account.custom_rules JSONB dict (may be empty).

    Returns:
        The name of the violated rule as a string, or None if all rules pass.
    """
    action_type: str = decision.get("action_type", "")
    current: float | None = decision.get("current_value")
    recommended: float | None = decision.get("recommended_value")

    # Rule: never_pause_brand_campaign
    if custom_rules.get("never_pause_brand_campaign") and action_type == "pause_campaign":
        return "never_pause_brand_campaign"

    # Rule: competitor_bidding_allowed
    if not custom_rules.get("competitor_bidding_allowed", True):
        if action_type in ("add_keyword", "increase_bid") and decision.get("is_competitor_keyword"):
            logger.debug("[manager] Blocked competitor keyword action — competitor_bidding_allowed=False")
            return "competitor_bidding_allowed"

    # Rule: max_cpc_increase_pct
    max_cpc_pct = custom_rules.get("max_cpc_increase_pct")
    if (
        max_cpc_pct is not None
        and action_type == "increase_bid"
        and current is not None
        and recommended is not None
        and current > 0
    ):
        actual_increase_pct = (recommended - current) / current * 100
        if actual_increase_pct > max_cpc_pct:
            logger.debug(
                "[manager] increase_bid blocked: %.2f%% increase exceeds max_cpc_increase_pct (%.2f%%)",
                actual_increase_pct,
                max_cpc_pct,
            )
            return "max_cpc_increase_pct"

    # Rule: max_daily_spend_increase_pct
    max_budget_pct = custom_rules.get("max_daily_spend_increase_pct")
    if (
        max_budget_pct is not None
        and action_type == "increase_budget"
        and current is not None
        and recommended is not None
        and current > 0
    ):
        actual_increase_pct = (recommended - current) / current * 100
        if actual_increase_pct > max_budget_pct:
            logger.debug(
                "[manager] increase_budget blocked: %.2f%% increase exceeds max_daily_spend_increase_pct (%.2f%%)",
                actual_increase_pct,
                max_budget_pct,
            )
            return "max_daily_spend_increase_pct"

    return None


def _validate_decision_payload(decision: dict[str, Any]) -> str | None:
    """Validate that a decision payload is internally coherent.

    Returns the rejection reason as a string, or None if valid.
    """
    action_type: str = decision.get("action_type", "")
    current: float | None = decision.get("current_value")
    recommended: float | None = decision.get("recommended_value")

    allowed_action_types = {
        "increase_bid", "decrease_bid", "increase_budget", "decrease_budget",
        "pause_campaign", "pause_adgroup", "enable_adgroup",
        "add_keyword", "add_negative_keyword", "adjust_match_type", "create_campaign",
    }

    if action_type not in allowed_action_types:
        return f"unknown_action_type:{action_type}"

    # Bid/budget increases must actually increase the value
    if action_type == "increase_bid":
        if current is None or recommended is None:
            return "increase_bid_missing_values"
        if recommended <= current:
            return "increase_bid_not_higher_than_current"

    if action_type == "increase_budget":
        if recommended is not None and recommended <= 0:
            return "increase_budget_invalid_value"
        if current is not None and recommended is not None and recommended <= current:
            return "increase_budget_not_higher_than_current"

    # pause_campaign requires reasoning
    if action_type == "pause_campaign" and not decision.get("reasoning"):
        return "pause_campaign_missing_reasoning"

    return None


# ── GAQL row parsers ───────────────────────────────────────────────────────────

def _parse_campaign_row(row: Any) -> dict[str, Any]:
    """Convert a CAMPAIGN_PERFORMANCE_7D proto-plus row into a plain dict.

    Args:
        row: A GoogleAdsRow proto-plus object returned by AdsClient.run_query().

    Returns:
        A flat dict representing one campaign's 7-day aggregate metrics.
    """
    return {
        "campaign_id": str(row.campaign.id),
        "campaign_name": row.campaign.name,
        "status": row.campaign.status.name,
        "budget_micros": row.campaign_budget.amount_micros or 0,
        "impressions": row.metrics.impressions,
        "clicks": row.metrics.clicks,
        "cost_micros": row.metrics.cost_micros or 0,
        "conversions": float(row.metrics.conversions or 0),
        "ctr": float(row.metrics.ctr or 0),
        "avg_cpc_micros": row.metrics.average_cpc or 0,
        "cost_per_conversion": float(row.metrics.cost_per_conversion or 0),
        "conversion_rate": float(row.metrics.conversions_from_interactions_rate or 0),
        "search_impression_share": float(row.metrics.search_impression_share or 0),
    }


def _parse_adgroup_row(row: Any) -> dict[str, Any]:
    """Convert an ADGROUP_BIDS proto-plus row into a plain dict.

    Args:
        row: A GoogleAdsRow proto-plus object returned by AdsClient.run_query().

    Returns:
        A flat dict representing one ad group's bid and 7-day performance.
    """
    return {
        "adgroup_id": str(row.ad_group.id),
        "adgroup_name": row.ad_group.name,
        "adgroup_status": row.ad_group.status.name,
        "cpc_bid_micros": row.ad_group.cpc_bid_micros or 0,
        "campaign_id": str(row.campaign.id),
        "campaign_name": row.campaign.name,
        "impressions": row.metrics.impressions,
        "clicks": row.metrics.clicks,
        "ctr": float(row.metrics.ctr or 0),
        "conversions": float(row.metrics.conversions or 0),
        "avg_cpc_micros": row.metrics.average_cpc or 0,
    }


# ── User message builder ───────────────────────────────────────────────────────

def _build_manager_user_message(
    context: str,
    campaigns: list[dict[str, Any]],
    adgroups: list[dict[str, Any]],
) -> str:
    """Compose the full user message sent to Claude for optimisation analysis.

    Args:
        context: Pre-built client context string from build_client_context().
        campaigns: Parsed campaign metric dicts from CAMPAIGN_PERFORMANCE_7D.
        adgroups: Parsed ad group bid dicts from ADGROUP_BIDS.

    Returns:
        A structured multi-section string ready to send as the Claude user turn.
    """
    def _format_campaigns(rows: list[dict[str, Any]]) -> str:
        if not rows:
            return "  (no campaign data)"
        lines: list[str] = []
        for c in rows:
            cpc_zar = c["avg_cpc_micros"] / config.MICROS_DIVISOR
            budget_zar = c["budget_micros"] / config.MICROS_DIVISOR
            cost_zar = c["cost_micros"] / config.MICROS_DIVISOR
            cpa_zar = c["cost_per_conversion"] / config.MICROS_DIVISOR if c["cost_per_conversion"] else 0
            lines.append(
                f"  Campaign: \"{c['campaign_name']}\" (ID: {c['campaign_id']})\n"
                f"    Status:                 {c['status']}\n"
                f"    Daily Budget:           R{budget_zar:,.2f}\n"
                f"    7d Spend:               R{cost_zar:,.2f}\n"
                f"    Impressions:            {c['impressions']:,}\n"
                f"    Clicks:                 {c['clicks']:,}\n"
                f"    CTR:                    {c['ctr']:.4%}\n"
                f"    Avg CPC:                R{cpc_zar:,.4f}\n"
                f"    Conversions:            {c['conversions']:.2f}\n"
                f"    Conversion Rate:        {c['conversion_rate']:.4%}\n"
                f"    Cost per Conversion:    R{cpa_zar:,.2f}\n"
                f"    Search Impression Share:{c['search_impression_share']:.2%}"
            )
        return "\n\n".join(lines)

    def _format_adgroups(rows: list[dict[str, Any]]) -> str:
        if not rows:
            return "  (no ad group data)"
        lines: list[str] = []
        for ag in rows:
            bid_zar = ag["cpc_bid_micros"] / config.MICROS_DIVISOR
            cpc_zar = ag["avg_cpc_micros"] / config.MICROS_DIVISOR
            lines.append(
                f"  Ad Group: \"{ag['adgroup_name']}\" (ID: {ag['adgroup_id']})\n"
                f"    Campaign:    {ag['campaign_name']} (ID: {ag['campaign_id']})\n"
                f"    Status:      {ag['adgroup_status']}\n"
                f"    CPC Bid:     R{bid_zar:,.4f}  ({ag['cpc_bid_micros']:,} micros)\n"
                f"    Avg CPC:     R{cpc_zar:,.4f}\n"
                f"    Impressions: {ag['impressions']:,}\n"
                f"    Clicks:      {ag['clicks']:,}\n"
                f"    CTR:         {ag['ctr']:.4%}\n"
                f"    Conversions: {ag['conversions']:.2f}"
            )
        return "\n\n".join(lines)

    return f"""
{context}

=== CAMPAIGN PERFORMANCE — Last 7 Days ===
{_format_campaigns(campaigns)}

=== AD GROUP BIDS — Last 7 Days ===
{_format_adgroups(adgroups)}

=== INSTRUCTIONS ===
Analyse the campaign and ad group data above against this client's goals,
baselines, and hard rules. Recommend the minimum set of bid and budget changes
needed to move the account toward its primary KPI target.

Express all monetary recommended_value and current_value fields in ZAR micros.
If nothing needs changing, return {{ "decisions": [] }}.
Return ONLY the JSON object.
""".strip()
