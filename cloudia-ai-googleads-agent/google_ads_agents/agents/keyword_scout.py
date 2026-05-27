"""Keyword Scout agent — identifies keyword opportunities from search terms.

Scheduled: Sunday 09:00 SAST.

Flow:
1. Pull search terms report via SEARCH_TERMS_30D
2. Pull existing keyword performance via KEYWORD_PERFORMANCE_30D
3. Build rich client context via build_client_context()
4. Send all data to Claude → structured JSON with three recommendation categories
5. Write each recommendation to approval_queue (status: pending)
6. Return a count of total recommendations created
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

import config
from agents.base import AgentRunResult, BaseAgent
from ai.claude import ClaudeClient
from ai.context_builder import build_client_context
from ai.prompts.keyword_scout import KEYWORD_SCOUT_SYSTEM_PROMPT
from db.models import Account, ApprovalQueue, IndustryBenchmark
from google_ads.client import AdsClient
from google_ads.queries import KEYWORD_PERFORMANCE_30D, SEARCH_TERMS_30D

logger = logging.getLogger(__name__)

# Mapping from Claude response keys → approval_queue action_type values
_ACTION_TYPE_MAP: dict[str, str] = {
    "new_keyword_opportunities": "add_keyword",
    "negatives_to_add": "add_negative_keyword",
    "match_type_adjustments": "adjust_match_type",
}


class KeywordScoutAgent(BaseAgent):
    """Mines the search terms report for keyword opportunities and writes queue items.

    For each account, the agent:
    - Identifies high-intent search terms not yet captured as keywords
    - Flags irrelevant terms that should be added as negative keywords
    - Spots keywords where a match type change would improve performance

    All recommendations land in approval_queue with status 'pending'.
    Nothing executes until a human approves via the dashboard.
    """

    name = "keyword_scout"

    def execute(self, account: Account) -> AgentRunResult:
        """Run the keyword scout pipeline for one account.

        Args:
            account: The Account ORM row for the client being analysed.

        Returns:
            AgentRunResult with decisions_generated set to the number of queue
            items written.
        """
        logger.info(
            "[keyword_scout] Starting keyword scout for %s", account.client_name
        )

        # ── 1. Pull search terms (last 30 days) ───────────────────────────────
        search_term_rows = self.ads.run_query(
            account.customer_id, SEARCH_TERMS_30D
        )
        if not search_term_rows:
            logger.warning(
                "[keyword_scout] No search term data for %s — skipping",
                account.client_name,
            )
            return AgentRunResult(
                agent_name=self.name,
                account_id=account.id,
                status="success",
                summary="No search term data returned — keyword scout skipped",
            )

        search_terms = [_parse_search_term_row(r) for r in search_term_rows]
        logger.debug(
            "[keyword_scout] Parsed %d search terms for %s",
            len(search_terms),
            account.client_name,
        )

        # ── 2. Pull existing keyword performance ───────────────────────────────
        keyword_rows = self.ads.run_query(
            account.customer_id, KEYWORD_PERFORMANCE_30D
        )
        keywords = [_parse_keyword_row(r) for r in keyword_rows]
        logger.debug(
            "[keyword_scout] Parsed %d existing keywords for %s",
            len(keywords),
            account.client_name,
        )

        # ── 3. Build client context ────────────────────────────────────────────
        benchmarks = self._get_benchmarks(account.industry)
        context = build_client_context(account, benchmarks)

        # ── 4. Send to Claude → structured recommendation JSON ─────────────────
        recommendations, tokens_used = self._generate_recommendations(
            context=context,
            search_terms=search_terms,
            keywords=keywords,
            account=account,
        )

        # ── 5. Write each recommendation to approval_queue ────────────────────
        total_queued = self._write_queue_items(account, recommendations)

        logger.info(
            "[keyword_scout] Queued %d recommendations for %s",
            total_queued,
            account.client_name,
        )

        summary = (
            f"Keyword scout completed for {account.client_name}: "
            f"{len(search_terms)} search terms analysed, "
            f"{len(keywords)} existing keywords reviewed, "
            f"{total_queued} recommendations queued for approval."
        )

        return AgentRunResult(
            agent_name=self.name,
            account_id=account.id,
            status="success",
            tokens_used=tokens_used,
            cost_usd=self.claude.estimate_cost_usd(tokens_used),
            decisions_generated=total_queued,
            summary=summary,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _generate_recommendations(
        self,
        context: str,
        search_terms: list[dict[str, Any]],
        keywords: list[dict[str, Any]],
        account: Account,
    ) -> tuple[dict[str, Any], int]:
        """Build the Claude user message and return parsed recommendation JSON.

        Args:
            context: Pre-built client context string from build_client_context().
            search_terms: Parsed search term dicts from SEARCH_TERMS_30D.
            keywords: Parsed keyword dicts from KEYWORD_PERFORMANCE_30D.
            account: The Account ORM row (used for logging only).

        Returns:
            Tuple of (recommendations_dict, total_tokens_used).

        Raises:
            ValueError: If Claude returns a response that cannot be parsed as JSON.
        """
        user_message = _build_scout_user_message(
            context=context,
            search_terms=search_terms,
            keywords=keywords,
        )

        logger.debug(
            "[keyword_scout] Calling Claude for %s (%d search terms, %d keywords)",
            account.client_name,
            len(search_terms),
            len(keywords),
        )

        result, tokens = self.claude.complete_json(
            system_prompt=KEYWORD_SCOUT_SYSTEM_PROMPT,
            user_message=user_message,
        )

        logger.debug(
            "[keyword_scout] Claude returned recommendations for %s (%d tokens)",
            account.client_name,
            tokens,
        )
        return result, tokens

    def _write_queue_items(
        self,
        account: Account,
        recommendations: dict[str, Any],
    ) -> int:
        """Persist all recommendation categories as approval_queue rows.

        Iterates over the three response keys from Claude and maps each item to
        the correct action_type.  All items are written with status='pending'.

        Args:
            account: The Account ORM row — provides account_id.
            recommendations: The parsed JSON dict returned by Claude.

        Returns:
            Total number of ApprovalQueue rows created across all categories.
        """
        total_queued = 0
        now = datetime.now(timezone.utc)

        for response_key, action_type in _ACTION_TYPE_MAP.items():
            items: list[dict[str, Any]] = recommendations.get(response_key, [])

            if not isinstance(items, list):
                logger.warning(
                    "[keyword_scout] Expected list for '%s', got %s — skipping",
                    response_key,
                    type(items).__name__,
                )
                continue

            for item in items:
                if not isinstance(item, dict):
                    logger.warning(
                        "[keyword_scout] Skipping non-dict item in '%s': %r",
                        response_key,
                        item,
                    )
                    continue

                reasoning: str = item.get("reasoning", "")

                queue_item = ApprovalQueue(
                    account_id=account.id,
                    agent_name=self.name,
                    action_type=action_type,
                    action_payload=item,
                    reasoning=reasoning,
                    status=config.QUEUE_STATUS_PENDING,
                )
                self.db.add(queue_item)
                total_queued += 1

                logger.debug(
                    "[keyword_scout] Queued %s: %r",
                    action_type,
                    item.get("keyword_text", item),
                )

        self.db.commit()
        return total_queued

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

def _parse_search_term_row(row: Any) -> dict[str, Any]:
    """Convert a SEARCH_TERMS_30D proto-plus row into a plain dict.

    Args:
        row: A GoogleAdsRow proto-plus object returned by AdsClient.run_query().

    Returns:
        A flat dict representing one search term entry.
    """
    return {
        "search_term": row.search_term_view.search_term,
        "status": row.search_term_view.status.name,
        "campaign_name": row.campaign.name,
        "ad_group_name": row.ad_group.name,
        "impressions": row.metrics.impressions,
        "clicks": row.metrics.clicks,
        "conversions": float(row.metrics.conversions or 0),
        "cost_micros": row.metrics.cost_micros or 0,
        "ctr": float(row.metrics.ctr or 0),
        "avg_cpc_micros": row.metrics.average_cpc or 0,
    }


def _parse_keyword_row(row: Any) -> dict[str, Any]:
    """Convert a KEYWORD_PERFORMANCE_30D proto-plus row into a plain dict.

    Args:
        row: A GoogleAdsRow proto-plus object returned by AdsClient.run_query().

    Returns:
        A flat dict representing one existing keyword's performance.
    """
    quality_score: int | None = None
    try:
        quality_score = row.ad_group_criterion.quality_info.quality_score
        if quality_score == 0:
            quality_score = None
    except AttributeError:
        pass

    return {
        "keyword_text": row.ad_group_criterion.keyword.text,
        "match_type": row.ad_group_criterion.keyword.match_type.name,
        "quality_score": quality_score,
        "status": row.ad_group_criterion.status.name,
        "campaign_name": row.campaign.name,
        "ad_group_name": row.ad_group.name,
        "impressions": row.metrics.impressions,
        "clicks": row.metrics.clicks,
        "ctr": float(row.metrics.ctr or 0),
        "avg_cpc_micros": row.metrics.average_cpc or 0,
        "conversions": float(row.metrics.conversions or 0),
        "cost_per_conversion_micros": float(row.metrics.cost_per_conversion or 0),
    }


# ── User message builder ───────────────────────────────────────────────────────

def _build_scout_user_message(
    context: str,
    search_terms: list[dict[str, Any]],
    keywords: list[dict[str, Any]],
) -> str:
    """Compose the full user message sent to Claude for keyword opportunity analysis.

    Args:
        context: Pre-built client context string from build_client_context().
        search_terms: Parsed search term dicts from SEARCH_TERMS_30D.
        keywords: Parsed keyword dicts from KEYWORD_PERFORMANCE_30D.

    Returns:
        A structured multi-section string ready to send as the Claude user turn.
    """
    def _format_search_terms(terms: list[dict[str, Any]]) -> str:
        if not terms:
            return "  (no search term data)"
        lines: list[str] = []
        for t in terms:
            lines.append(
                f"  Term: \"{t['search_term']}\"\n"
                f"    Campaign:    {t['campaign_name']}\n"
                f"    Ad Group:    {t['ad_group_name']}\n"
                f"    Status:      {t['status']}\n"
                f"    Impressions: {t['impressions']:,}\n"
                f"    Clicks:      {t['clicks']:,}\n"
                f"    CTR:         {t['ctr']:.4%}\n"
                f"    Conversions: {t['conversions']:.2f}\n"
                f"    Cost (micros): {t['cost_micros']:,}"
            )
        return "\n\n".join(lines)

    def _format_keywords(kws: list[dict[str, Any]]) -> str:
        if not kws:
            return "  (no keyword data)"
        lines: list[str] = []
        for k in kws:
            qs_str = str(k["quality_score"]) if k["quality_score"] is not None else "n/a"
            lines.append(
                f"  Keyword: \"{k['keyword_text']}\" [{k['match_type']}]\n"
                f"    Campaign:      {k['campaign_name']}\n"
                f"    Ad Group:      {k['ad_group_name']}\n"
                f"    Status:        {k['status']}\n"
                f"    Quality Score: {qs_str}\n"
                f"    Impressions:   {k['impressions']:,}\n"
                f"    Clicks:        {k['clicks']:,}\n"
                f"    CTR:           {k['ctr']:.4%}\n"
                f"    Conversions:   {k['conversions']:.2f}\n"
                f"    Cost/Conv (micros): {k['cost_per_conversion_micros']:,.0f}"
            )
        return "\n\n".join(lines)

    return f"""
{context}

=== SEARCH TERMS REPORT (Last 30 Days, impressions > 10) ===
These are actual user queries that triggered your ads.

{_format_search_terms(search_terms)}

=== EXISTING KEYWORDS (Last 30 Days) ===
These are the keywords currently active in the account.

{_format_keywords(keywords)}

=== INSTRUCTIONS ===
Analyse the search terms above against the existing keyword list.
Identify:
1. High-value search terms not yet captured as exact/phrase/broad keywords
2. Irrelevant or low-quality terms that should become negative keywords
3. Existing keywords where a match type change would improve targeting or efficiency

Respect all custom_rules defined in the client context above.
Return ONLY the JSON object with the three arrays as specified.
""".strip()
