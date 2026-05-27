"""SEO Content Agent — long-form keyword-optimised blog articles."""
from sqlalchemy.orm import Session

from backend.agents.base import BaseAgent, AgentError
from backend.db.models import ContentCalendar, Campaign, Client, BrandGuidelines, ContentAsset
from backend.ai import claude
from backend.ai.context_builder import build_campaign_context
from backend.ai.prompts.seo_content import SEO_ARTICLE_PROMPT


class SEOContentAgent(BaseAgent):
    name = "seo_content"

    def run(self, calendar_id: int) -> dict:
        cal = self.db.get(ContentCalendar, calendar_id)
        if not cal:
            raise AgentError(f"Calendar item {calendar_id} not found")

        campaign = self.db.get(Campaign, cal.campaign_id)
        client = self.db.get(Client, cal.client_id)
        guidelines = self.db.query(BrandGuidelines).filter_by(client_id=cal.client_id).first()

        self._start_task(campaign.id, calendar_id, {"calendar_id": calendar_id}, pipeline_order=10)
        context = build_campaign_context(client, campaign, guidelines)

        prompt = SEO_ARTICLE_PROMPT.format(
            keyword=cal.topic or "industry insights",
            word_count=1200,
        )

        result, inp, out, cost = claude.call_json(system_prompt=context, user_prompt=prompt, max_tokens=6000)
        self._track_tokens(inp, out, cost)

        meta_title = result.get("meta_title", "")
        meta_desc = result.get("meta_description", "")

        if len(meta_title) > 60:
            meta_title = meta_title[:60]
        if len(meta_desc) > 160:
            meta_desc = meta_desc[:160]

        full_content = f"# {result.get('headline', '')}\n\n{result.get('body', '')}"
        asset = ContentAsset(
            campaign_id=campaign.id,
            client_id=cal.client_id,
            asset_type="text",
            content_type="article",
            title=result.get("headline", ""),
            text_content=full_content,
            platform_versions={
                "meta_title": meta_title,
                "meta_description": meta_desc,
                "excerpt": result.get("excerpt", ""),
            },
            status="draft",
            tokens_used=self._total_tokens,
            cost_usd=round(self._total_cost, 6),
            created_by_agent=self.name,
        )
        self.db.add(asset)
        cal.status = "created"
        self.db.flush()
        cal.asset_id = asset.id
        self.db.commit()

        self._complete_task({"asset_id": asset.id})
        return {"asset_id": asset.id}
