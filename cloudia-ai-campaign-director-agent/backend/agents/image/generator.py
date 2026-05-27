"""Image Generator Agent — DALL-E 3 / Flux AI image generation."""
import logging
from sqlalchemy.orm import Session

from backend.agents.base import BaseAgent, AgentError
from backend.db.models import ContentCalendar, Campaign, Client, BrandGuidelines, ContentAsset
from backend.ai import claude, dalle
from backend.ai.context_builder import build_campaign_context
from backend.ai.prompts.image_generator import IMAGE_PROMPT_GENERATION
from backend.media import storage

logger = logging.getLogger(__name__)
MAX_RETRIES = 1


class ImageGeneratorAgent(BaseAgent):
    name = "image_generator"

    def run(self, calendar_id: int) -> dict:
        cal = self.db.get(ContentCalendar, calendar_id)
        if not cal:
            raise AgentError(f"Calendar item {calendar_id} not found")

        campaign = self.db.get(Campaign, cal.campaign_id)
        client = self.db.get(Client, cal.client_id)
        guidelines = self.db.query(BrandGuidelines).filter_by(client_id=cal.client_id).first()

        self._start_task(campaign.id, calendar_id, {"calendar_id": calendar_id}, pipeline_order=15)
        context = build_campaign_context(client, campaign, guidelines)

        prompt_req = IMAGE_PROMPT_GENERATION.format(
            content_type=cal.content_type,
            topic=cal.topic or "brand lifestyle",
            image_style_notes=(guidelines.image_style_notes or "professional, clean") if guidelines else "professional, clean",
            primary_colour=(guidelines.primary_colour or "#000000") if guidelines else "#000000",
        )

        prompt_result, inp, out, cost = claude.call_json(system_prompt=context, user_prompt=prompt_req)
        self._track_tokens(inp, out, cost)
        dalle_prompt = prompt_result.get("prompt", cal.topic or "professional brand image")

        for attempt in range(MAX_RETRIES + 1):
            try:
                image_bytes, model_used, img_cost = dalle.generate_image(dalle_prompt)
                self._total_cost += img_cost
                break
            except Exception as exc:
                if attempt == MAX_RETRIES:
                    self._fail_task(f"Image generation failed: {exc}")
                    raise AgentError(f"Image generation failed after retries: {exc}") from exc
                logger.warning("Image gen attempt %d failed: %s — retrying", attempt + 1, exc)

        filename = f"{cal.id}_raw.jpg"
        obj_path = storage.object_path(cal.client_id, campaign.id, "raw", "images", filename)
        storage.upload(image_bytes, obj_path, content_type="image/jpeg")

        asset = ContentAsset(
            campaign_id=campaign.id,
            client_id=cal.client_id,
            asset_type="image",
            content_type="generated_image",
            storage_path=obj_path,
            storage_bucket=None,
            format="jpg",
            status="draft",
            generation_prompt=dalle_prompt,
            generation_model=model_used,
            tokens_used=self._total_tokens,
            cost_usd=round(self._total_cost, 6),
            created_by_agent=self.name,
        )
        self.db.add(asset)
        cal.status = "created"
        self.db.flush()
        cal.asset_id = asset.id
        self.db.commit()

        self._complete_task({"asset_id": asset.id, "model": model_used})
        return {"asset_id": asset.id, "model": model_used}
