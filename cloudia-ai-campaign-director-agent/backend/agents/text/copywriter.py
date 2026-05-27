"""Copywriter Agent — captions, hashtags, CTA for social posts."""
import logging
from sqlalchemy.orm import Session

from backend.agents.base import BaseAgent, AgentError
from backend.db.models import ContentCalendar, Campaign, Client, BrandGuidelines, ContentAsset
from backend.ai import claude
from backend.ai.context_builder import build_campaign_context
from backend.ai.prompts.copywriter import COPYWRITER_PROMPT
from backend.config import PLATFORM_SPECS

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


class CopywriterAgent(BaseAgent):
    name = "copywriter"

    def run(self, calendar_id: int) -> dict:
        cal = self.db.get(ContentCalendar, calendar_id)
        if not cal:
            raise AgentError(f"Calendar item {calendar_id} not found")

        campaign = self.db.get(Campaign, cal.campaign_id)
        client = self.db.get(Client, cal.client_id)
        guidelines = self.db.query(BrandGuidelines).filter_by(client_id=cal.client_id).first()

        task = self._start_task(campaign.id, calendar_id, {"calendar_id": calendar_id}, pipeline_order=10)
        context = build_campaign_context(client, campaign, guidelines)

        platform_cfg = PLATFORM_SPECS.get(cal.platform, {})
        max_chars = platform_cfg.get("caption_max_chars", 2200)
        max_hashtags = platform_cfg.get("hashtag_max", 30)
        required_hashtags = (guidelines.required_elements or {}).get("hashtags_required", []) if guidelines else []
        campaign_hashtags = campaign.campaign_hashtags or []

        prompt = COPYWRITER_PROMPT.format(
            platform=cal.platform,
            content_type=cal.content_type,
            topic=cal.topic or "general brand content",
            max_chars=max_chars,
            required_hashtags=", ".join(required_hashtags),
            campaign_hashtags=", ".join(campaign_hashtags),
            max_hashtags=max_hashtags,
            goal=campaign.goal or "engagement",
        )

        for attempt in range(MAX_RETRIES + 1):
            result, inp, out, cost = claude.call_json(system_prompt=context, user_prompt=prompt)
            self._track_tokens(inp, out, cost)

            caption = result.get("caption", "")
            hashtags = result.get("hashtags", [])

            issues = self._validate(caption, hashtags, guidelines, max_chars, required_hashtags, campaign_hashtags)
            if not issues:
                break
            if attempt == MAX_RETRIES:
                self._fail_task(f"Copy validation failed after {MAX_RETRIES + 1} attempts: {issues}")
                raise AgentError(f"Copy validation failed: {issues}")
            logger.warning("Copywriter attempt %d failed validation: %s — retrying", attempt + 1, issues)

        asset = ContentAsset(
            campaign_id=campaign.id,
            client_id=cal.client_id,
            asset_type="text",
            content_type="caption",
            text_content=caption,
            platform_versions={cal.platform: {"caption": caption, "hashtags": hashtags}},
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
        return {"asset_id": asset.id, "calendar_id": calendar_id}

    def _validate(self, caption: str, hashtags: list, guidelines, max_chars: int,
                  required_hashtags: list, campaign_hashtags: list) -> list[str]:
        issues = []
        if len(caption) > max_chars:
            issues.append(f"Caption {len(caption)} chars exceeds limit {max_chars}")

        all_text = caption + " " + " ".join(hashtags)
        forbidden = (guidelines.forbidden_words or []) if guidelines else []
        for word in forbidden:
            if word.lower() in all_text.lower():
                issues.append(f"Forbidden word found: {word!r}")

        competitors = (guidelines.competitor_names or []) if guidelines else []
        for name in competitors:
            if name.lower() in all_text.lower():
                issues.append(f"Competitor name found: {name!r}")

        for tag in required_hashtags + campaign_hashtags:
            if tag.lower() not in all_text.lower():
                issues.append(f"Required hashtag missing: {tag}")

        return issues
