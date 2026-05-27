"""Ad Copy Agent — 3 A/B variants per ad unit."""
from sqlalchemy.orm import Session

from backend.agents.base import BaseAgent, AgentError
from backend.db.models import ContentCalendar, Campaign, Client, BrandGuidelines, ContentAsset
from backend.ai import claude
from backend.ai.context_builder import build_campaign_context
from backend.ai.prompts.ad_copy import AD_COPY_PROMPT

HEADLINE_LIMITS = {"facebook": 40, "instagram": 40, "linkedin": 70, "google_business": 60, "twitter": 70}
BODY_LIMITS = {"facebook": 125, "instagram": 125, "linkedin": 600, "google_business": 1500, "twitter": 280}


class AdCopyAgent(BaseAgent):
    name = "ad_copy"

    def run(self, calendar_id: int) -> dict:
        cal = self.db.get(ContentCalendar, calendar_id)
        if not cal:
            raise AgentError(f"Calendar item {calendar_id} not found")

        campaign = self.db.get(Campaign, cal.campaign_id)
        client = self.db.get(Client, cal.client_id)
        guidelines = self.db.query(BrandGuidelines).filter_by(client_id=cal.client_id).first()

        self._start_task(campaign.id, calendar_id, {"calendar_id": calendar_id}, pipeline_order=10)
        context = build_campaign_context(client, campaign, guidelines)

        prompt = AD_COPY_PROMPT.format(
            platform=cal.platform,
            goal=campaign.goal or "lead_gen",
            target_audience=campaign.target_audience or client.target_audience or "",
            headline_limit=HEADLINE_LIMITS.get(cal.platform, 60),
            body_limit=BODY_LIMITS.get(cal.platform, 280),
        )

        variants, inp, out, cost = claude.call_json(system_prompt=context, user_prompt=prompt)
        self._track_tokens(inp, out, cost)

        if not isinstance(variants, list) or len(variants) < 3:
            self._fail_task("Ad copy returned fewer than 3 variants")
            raise AgentError("Ad copy must return exactly 3 variants")

        asset_ids = []
        for variant in variants[:3]:
            asset = ContentAsset(
                campaign_id=campaign.id,
                client_id=cal.client_id,
                asset_type="text",
                content_type="ad_copy",
                title=f"Ad Variant {variant.get('variant', '?')}",
                text_content=f"{variant.get('headline', '')}\n\n{variant.get('body', '')}",
                platform_versions={cal.platform: variant},
                status="draft",
                tokens_used=self._total_tokens // 3,
                cost_usd=round(self._total_cost / 3, 6),
                created_by_agent=self.name,
            )
            self.db.add(asset)
            self.db.flush()
            asset_ids.append(asset.id)

        cal.status = "created"
        self.db.commit()

        self._complete_task({"asset_ids": asset_ids})
        return {"asset_ids": asset_ids}
