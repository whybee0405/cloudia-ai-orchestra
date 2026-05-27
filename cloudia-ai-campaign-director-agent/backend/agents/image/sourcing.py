"""Image Sourcing Agent — Unsplash / Pexels stock photo sourcing."""
import logging
import httpx
from sqlalchemy.orm import Session

from backend.agents.base import BaseAgent, AgentError
from backend.db.models import ContentCalendar, Campaign, Client, BrandGuidelines, ContentAsset
from backend.ai import claude
from backend.ai.context_builder import build_campaign_context
from backend.ai.prompts.analytics import STOCK_SEARCH_QUERY_PROMPT
from backend.media import storage
from backend.config import get_settings

logger = logging.getLogger(__name__)

UNSPLASH_SEARCH = "https://api.unsplash.com/search/photos"
PEXELS_SEARCH = "https://api.pexels.com/v1/search"


class ImageSourcingAgent(BaseAgent):
    name = "image_sourcing"

    def run(self, calendar_id: int) -> dict:
        cal = self.db.get(ContentCalendar, calendar_id)
        if not cal:
            raise AgentError(f"Calendar item {calendar_id} not found")

        campaign = self.db.get(Campaign, cal.campaign_id)
        client = self.db.get(Client, cal.client_id)
        guidelines = self.db.query(BrandGuidelines).filter_by(client_id=cal.client_id).first()

        self._start_task(campaign.id, calendar_id, {"calendar_id": calendar_id}, pipeline_order=15)
        context = build_campaign_context(client, campaign, guidelines)

        queries, inp, out, cost = claude.call_json(
            system_prompt=context,
            user_prompt=STOCK_SEARCH_QUERY_PROMPT.format(topic=cal.topic or "business", industry=client.industry or ""),
        )
        self._track_tokens(inp, out, cost)

        settings = get_settings()
        image_bytes, attribution = None, {}

        for query in (queries or [cal.topic]):
            image_bytes, attribution = self._try_unsplash(query, settings.unsplash_access_key)
            if image_bytes:
                break

        if not image_bytes:
            for query in (queries or [cal.topic]):
                image_bytes, attribution = self._try_pexels(query, settings.pexels_api_key)
                if image_bytes:
                    break

        if not image_bytes:
            self._fail_task("No stock image found on Unsplash or Pexels")
            raise AgentError("No stock image found for topic")

        filename = f"{cal.id}_stock.jpg"
        obj_path = storage.object_path(cal.client_id, campaign.id, "raw", "images", filename)
        storage.upload(image_bytes, obj_path, content_type="image/jpeg")

        asset = ContentAsset(
            campaign_id=campaign.id,
            client_id=cal.client_id,
            asset_type="image",
            content_type="stock_image",
            storage_path=obj_path,
            format="jpg",
            status="draft",
            generation_prompt=str(attribution),
            created_by_agent=self.name,
        )
        self.db.add(asset)
        cal.status = "created"
        self.db.flush()
        cal.asset_id = asset.id
        self.db.commit()

        self._complete_task({"asset_id": asset.id, "attribution": attribution})
        return {"asset_id": asset.id}

    def _try_unsplash(self, query: str, key: str) -> tuple[bytes | None, dict]:
        if not key:
            return None, {}
        r = httpx.get(UNSPLASH_SEARCH, params={"query": query, "per_page": 1}, headers={"Authorization": f"Client-ID {key}"}, timeout=30)
        if r.status_code == 200 and r.json().get("results"):
            photo = r.json()["results"][0]
            img = httpx.get(photo["urls"]["regular"], timeout=60)
            return img.content, {"source": "unsplash", "photographer": photo["user"]["name"], "photo_id": photo["id"]}
        return None, {}

    def _try_pexels(self, query: str, key: str) -> tuple[bytes | None, dict]:
        if not key:
            return None, {}
        r = httpx.get(PEXELS_SEARCH, params={"query": query, "per_page": 1}, headers={"Authorization": key}, timeout=30)
        if r.status_code == 200 and r.json().get("photos"):
            photo = r.json()["photos"][0]
            img = httpx.get(photo["src"]["large"], timeout=60)
            return img.content, {"source": "pexels", "photographer": photo["photographer"], "photo_id": photo["id"]}
        return None, {}
