"""Master Digital Marketing Director Agent — cross-service suggestion engine."""
import logging
from uuid import UUID
from typing import Optional

import httpx

from app.agents.claude_client import ClaudeClient
from app.config import get_settings
from app.schemas import Suggestion, SuggestionsResponse

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Master Digital Marketing Director for a South African digital agency.
You analyse a client's current digital marketing state across three services — Social Campaigns, Google Ads, and Website — and provide prioritised recommendations.

Return ONLY valid JSON:
{
  "suggestions": [
    {
      "id": "unique_slug",
      "priority": 1,
      "service": "campaigns|ads|webdev|brand_dna",
      "title": "Short action title",
      "description": "1-2 sentence explanation of why this is important",
      "action_label": "Button label e.g. 'Create Campaign'",
      "action_url": "/clients/{client_id}/campaigns"
    }
  ]
}

Priority scale: 1=critical, 2=high, 3=medium, 4=low
Order suggestions by priority ascending (most critical first).
Limit to a maximum of 6 suggestions. Be specific and actionable."""


def _fetch_summary(url: str, secret: str) -> Optional[dict]:
    try:
        with httpx.Client(timeout=5) as client:
            resp = client.get(url, headers={"X-Internal-Secret": secret})
            if resp.status_code == 200:
                return resp.json()
    except Exception as exc:
        logger.debug("Summary fetch failed (%s): %s", url, exc)
    return None


def run_director(client_id: UUID, client_name: str, has_brand_dna: bool, persona_count: int) -> SuggestionsResponse:
    settings = get_settings()
    cid = str(client_id)

    campaigns_summary = _fetch_summary(
        f"{settings.campaigns_service_url}/api/campaigns/clients/by-brand-dna/{cid}/summary",
        settings.internal_api_secret,
    )
    ads_summary = _fetch_summary(
        f"{settings.ads_service_url}/api/ads/accounts/by-brand-dna/{cid}/summary",
        settings.internal_api_secret,
    )
    webdev_summary = _fetch_summary(
        f"{settings.webdev_service_url}/api/webdev/projects/clients/by-brand-dna/{cid}/summary",
        settings.internal_api_secret,
    )

    state = f"""Client: {client_name} (ID: {cid})

Brand DNA: {"Complete" if has_brand_dna else "MISSING — critical gap"}
ICP Personas: {persona_count} defined{"" if persona_count > 0 else " — NONE defined"}

Social Campaigns: {campaigns_summary or "Service not connected or no data yet"}
Google Ads: {ads_summary or "Service not connected or no data yet"}
Website Projects: {webdev_summary or "Service not connected or no data yet"}"""

    user_prompt = f"""Analyse this client's digital marketing state and return prioritised recommendations.

{state}

Return your suggestions as JSON. Use /clients/{cid}/ as the base for all action_url values."""

    claude = ClaudeClient()
    raw = claude.call_json(SYSTEM_PROMPT, user_prompt, max_tokens=2000)

    suggestions = [Suggestion(**s) for s in raw.get("suggestions", [])]
    return SuggestionsResponse(client_id=client_id, suggestions=suggestions)
