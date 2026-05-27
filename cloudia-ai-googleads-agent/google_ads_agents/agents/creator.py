"""Creator agent — on-demand only, triggered via POST /campaigns/create.

Unlike other agents, the Creator does not run on a schedule. It is called
directly by the API route with a campaign brief dict and produces a single
full campaign structure queued for human approval.

Flow:
1. Load account + matching IndustryBenchmark from DB
2. Build client context via build_client_context()
3. Send brief + context to Claude with CREATOR_SYSTEM_PROMPT
4. Claude returns campaign structure JSON:
   { campaign_name, campaign_settings, ad_groups: [...] }
5. Write to approval_queue as a single row
   (action_type='create_campaign', action_payload=full structure)
6. Return the queue item and the campaign structure dict
"""

import json
import logging

from sqlalchemy import select

import config
from agents.base import AgentRunResult, BaseAgent
from ai.context_builder import build_client_context
from ai.prompts.creator import CREATOR_SYSTEM_PROMPT
from db.models import Account, ApprovalQueue, IndustryBenchmark
from db.queue import write_queue_item

logger = logging.getLogger(__name__)


class CreatorAgent(BaseAgent):
    """Generates a complete campaign structure from a human-authored brief.

    This agent is intentionally excluded from the automated schedule. Every
    call must originate from a human-initiated API request (POST /campaigns/create)
    so that a brief with business intent is always provided.

    The resulting campaign structure is queued for approval before any Google
    Ads API call is made — consistent with the rest of the system.
    """

    name = "creator"

    # ── Public API ─────────────────────────────────────────────────────────────

    def create_from_brief(
        self,
        account: Account,
        brief: dict,
    ) -> tuple[ApprovalQueue, dict]:
        """Generate a campaign structure from a brief and queue it for approval.

        This is the only valid entry point for the Creator agent. It is called
        directly by the API route handler — never via run().

        Args:
            account: The Account ORM row for the client the campaign is for.
            brief: Campaign brief dict containing at minimum:
                   goal, product_service, audience_description, budget_daily_zar,
                   geo_targets, languages, landing_page_url.

        Returns:
            A tuple of (ApprovalQueue row, campaign_structure dict).
            The queue item is already committed with status='pending'.

        Raises:
            ValueError: If the brief is invalid, Claude returns non-JSON,
                        or the campaign structure fails validation.
        """
        logger.info(
            "[creator] Starting for account %s (id=%d)",
            account.client_name,
            account.id,
        )

        # ── 0. Validate the brief before calling Claude ───────────────────────
        _validate_brief(brief)

        # ── 1. Load industry benchmarks ───────────────────────────────────────
        benchmarks = self._get_benchmarks(account.industry)

        # ── 2. Build client context ───────────────────────────────────────────
        context = build_client_context(account, benchmarks)

        # ── 3. Send to Claude → campaign structure JSON ───────────────────────
        campaign_structure, tokens_used = self._generate_campaign_structure(
            context=context,
            brief=brief,
            account=account,
        )

        # ── 4. Validate the returned structure has the expected top-level keys ─
        _validate_campaign_structure(campaign_structure)

        # ── 5. Write to approval_queue ────────────────────────────────────────
        reasoning = (
            f"Campaign structure generated from brief for account '{account.client_name}'. "
            f"Goal: {brief.get('goal', 'not specified')}. "
            f"Product/Service: {brief.get('product_service', 'not specified')}. "
            f"Daily budget: R{brief.get('budget_daily_zar', 'not specified')}. "
            f"Campaign name proposed: {campaign_structure.get('campaign_name', 'unnamed')}. "
            f"Ad groups: {len(campaign_structure.get('ad_groups', []))}."
        )

        queue_item = write_queue_item(
            db=self.db,
            account_id=account.id,
            agent_name=self.name,
            action_type="create_campaign",
            action_payload=campaign_structure,
            reasoning=reasoning,
        )

        logger.info(
            "[creator] Queued campaign structure as item id=%d for %s "
            "(%d ad groups, %d tokens used)",
            queue_item.id,
            account.client_name,
            len(campaign_structure.get("ad_groups", [])),
            tokens_used,
        )

        return queue_item, campaign_structure

    def execute(self, account: Account) -> AgentRunResult:
        """Not implemented — Creator is triggered only via create_from_brief().

        Raises:
            NotImplementedError: Always. Use create_from_brief() instead.
        """
        raise NotImplementedError("Creator must be called via create_from_brief()")

    # ── Private helpers ────────────────────────────────────────────────────────

    def _generate_campaign_structure(
        self,
        context: str,
        brief: dict,
        account: Account,
    ) -> tuple[dict, int]:
        """Build the Claude user message and return the parsed campaign structure.

        Args:
            context: Pre-built client context string from build_client_context().
            brief: Campaign brief dict from the API request.
            account: The Account ORM row (used for logging).

        Returns:
            Tuple of (campaign_structure_dict, total_tokens_used).

        Raises:
            ValueError: If Claude's response cannot be parsed as JSON.
        """
        user_message = _build_creator_user_message(context=context, brief=brief)

        logger.debug(
            "[creator] Calling Claude for %s",
            account.client_name,
        )

        # Creator needs more tokens than standard agents because the full
        # campaign structure (ad groups, keywords, ads) is verbose JSON.
        campaign_structure, tokens = self.claude.complete_json(
            system_prompt=CREATOR_SYSTEM_PROMPT,
            user_message=user_message,
            max_tokens=4096,
        )

        logger.debug(
            "[creator] Claude returned structure with %d ad groups for %s (%d tokens)",
            len(campaign_structure.get("ad_groups", [])),
            account.client_name,
            tokens,
        )
        return campaign_structure, tokens

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


# ── Validation ─────────────────────────────────────────────────────────────────

def _validate_brief(brief: dict) -> None:
    """Validate the campaign brief before calling Claude.

    Raises:
        ValueError: If the brief is missing required fields or has invalid values.
    """
    budget = brief.get("budget_daily_zar")
    if budget is None or (isinstance(budget, (int, float)) and budget <= 0):
        raise ValueError(
            f"brief.budget_daily_zar must be greater than 0 (got {budget!r})"
        )

    required_fields = {"goal", "product_service", "audience_description", "landing_page_url"}
    missing = required_fields - set(brief.keys())
    if missing:
        raise ValueError(f"Campaign brief is missing required fields: {missing}")

    for field in required_fields:
        if not brief.get(field):
            raise ValueError(f"Campaign brief field '{field}' cannot be empty")


def _validate_campaign_structure(structure: dict) -> None:
    """Assert that the campaign structure meets all Google Ads constraints.

    Raises:
        ValueError: If any required key is missing, ad_groups is empty,
                    or any ad copy exceeds Google Ads character limits.
    """
    required = {"campaign_name", "campaign_settings", "ad_groups"}
    missing = required - set(structure.keys())
    if missing:
        raise ValueError(
            f"Claude campaign structure is missing required keys: {missing}. "
            f"Got keys: {set(structure.keys())}"
        )
    if not isinstance(structure["ad_groups"], list):
        raise ValueError("campaign_structure.ad_groups must be a list")

    if len(structure["ad_groups"]) == 0:
        raise ValueError(
            "campaign_structure.ad_groups cannot be empty — "
            "Claude returned a campaign with no ad groups"
        )

    # Validate Google Ads character limits on all ad copy
    for ag in structure["ad_groups"]:
        for ad in ag.get("ads", []):
            for headline in ad.get("headlines", []):
                if len(headline) > 30:
                    raise ValueError(
                        f"headline exceeds 30 characters ({len(headline)}): {headline!r}"
                    )
            for desc in ad.get("descriptions", []):
                if len(desc) > 90:
                    raise ValueError(
                        f"description exceeds 90 characters ({len(desc)}): {desc[:50]!r}..."
                    )


# ── User message builder ───────────────────────────────────────────────────────

def _build_creator_user_message(context: str, brief: dict) -> str:
    """Compose the full user message sent to Claude for campaign creation.

    Args:
        context: Pre-built client context string from build_client_context().
        brief: Campaign brief dict from the API request.

    Returns:
        A structured multi-section string ready to send as the Claude user turn.
    """
    geo_targets_str = ", ".join(brief.get("geo_targets", [])) or "not specified"
    languages_str = ", ".join(brief.get("languages", [])) or "not specified"

    return f"""
{context}

=== CAMPAIGN BRIEF ===
Goal:                  {brief.get("goal", "not specified")}
Product / Service:     {brief.get("product_service", "not specified")}
Audience Description:  {brief.get("audience_description", "not specified")}
Daily Budget (ZAR):    R{brief.get("budget_daily_zar", "not specified")}
Geographic Targets:    {geo_targets_str}
Languages:             {languages_str}
Landing Page URL:      {brief.get("landing_page_url", "not specified")}

=== INSTRUCTIONS ===
Design a complete, ready-to-launch Google Ads campaign for this client based
on the brief above. Apply all hard rules from the client context without
exception. Return ONLY the JSON object — no preamble, no explanation.
""".strip()
