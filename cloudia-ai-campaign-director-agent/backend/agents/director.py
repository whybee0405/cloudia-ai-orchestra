"""Campaign Director Agent — validates brief, determines content mix, kicks off Planner."""
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from backend.agents.base import BaseAgent, AgentError
from backend.db.models import Campaign, Client, BrandGuidelines, PlatformAccount
from backend.ai import claude
from backend.ai.context_builder import build_campaign_context
from backend.ai.prompts.director import DIRECTOR_VALIDATE_PROMPT

logger = logging.getLogger(__name__)


class DirectorAgent(BaseAgent):
    name = "director"

    def run(self, campaign_id: int) -> dict:
        campaign = self.db.get(Campaign, campaign_id)
        if not campaign:
            raise AgentError(f"Campaign {campaign_id} not found")

        client = self.db.get(Client, campaign.client_id)
        guidelines = self.db.query(BrandGuidelines).filter_by(client_id=campaign.client_id).first()

        task = self._start_task(campaign_id, None, {"campaign_id": campaign_id}, pipeline_order=0)

        # Step 1: validate platform accounts
        missing_platforms = self._validate_platform_accounts(campaign, client)
        if missing_platforms:
            self._fail_task(f"Missing OAuth connections: {', '.join(missing_platforms)}")
            raise AgentError(f"Missing platform connections: {missing_platforms}")

        # Step 2: validate brief has sufficient info
        if not campaign.brief or not campaign.goal or not campaign.platforms:
            self._fail_task("Campaign brief is incomplete — goal, platforms, and brief are required.")
            raise AgentError("Campaign brief incomplete")

        if campaign.end_date and campaign.start_date and campaign.end_date < campaign.start_date:
            self._fail_task("end_date is before start_date")
            raise AgentError("end_date before start_date")

        if campaign.posts_per_week is not None and campaign.posts_per_week <= 0:
            self._fail_task("posts_per_week must be > 0")
            raise AgentError("posts_per_week <= 0")

        # Step 3: ask Claude for content mix suggestion
        context = build_campaign_context(client, campaign, guidelines)
        response, inp, out, cost = claude.call_json(
            system_prompt=context,
            user_prompt=DIRECTOR_VALIDATE_PROMPT,
        )
        self._track_tokens(inp, out, cost)

        # Step 4: apply content mix if not set
        if not campaign.content_mix and response.get("suggested_content_mix"):
            campaign.content_mix = response["suggested_content_mix"]

        campaign.status = "planning"
        self.db.commit()

        self._complete_task({"validation": response, "next": "planner"})
        return {"campaign_id": campaign_id, "status": "planning", "validation": response}

    def _validate_platform_accounts(self, campaign: Campaign, client: Client) -> list[str]:
        """Return list of platform names with no active account."""
        platforms: list[str] = campaign.platforms or []
        missing = []
        for platform in platforms:
            account = (
                self.db.query(PlatformAccount)
                .filter_by(client_id=client.id, platform=platform, is_active=True)
                .first()
            )
            if not account:
                missing.append(platform)
        return missing
