"""Brand DNA Enrichment Agent — analyses the business and suggests improvements."""
import logging
from typing import Optional
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from app.agents.claude_client import ClaudeClient
from app.schemas import EnrichmentResponse, EnrichmentSuggestion

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior brand strategist at a South African digital marketing agency.
You analyse businesses and suggest improvements to their Brand DNA — the core identity that shapes all their marketing output.

When given brand data, you:
1. Identify gaps (missing USPs, weak key messages, generic tone)
2. Suggest concrete improvements based on the industry and business context
3. Extract additional signals from the website text if provided
4. Always tailor suggestions to a South African market context

Return ONLY valid JSON matching this schema:
{
  "suggestions": [
    {
      "field": "field_name",
      "current_value": <current or null>,
      "suggested_value": <your suggestion>,
      "reasoning": "Brief explanation"
    }
  ],
  "summary": "One paragraph summary of the brand's current positioning and key gaps"
}"""


def _scrape_website(url: str) -> str:
    try:
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": "CloudIA BrandBot/1.0"})
            resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return text[:3000]
    except Exception as exc:
        logger.warning("Website scrape failed for %s: %s", url, exc)
        return ""


def run_enrichment(
    client_name: str,
    industry: Optional[str],
    website_url: Optional[str],
    brand_dna: dict,
) -> EnrichmentResponse:
    website_text = ""
    if website_url:
        website_text = _scrape_website(website_url)

    user_prompt = f"""Business: {client_name}
Industry: {industry or "Not specified"}

Current Brand DNA:
{brand_dna}

{"Website content (extracted):" + chr(10) + website_text if website_text else "No website content available."}

Analyse this brand and return enrichment suggestions as JSON."""

    claude = ClaudeClient()
    raw = claude.call_json(SYSTEM_PROMPT, user_prompt, max_tokens=3000)

    suggestions = [EnrichmentSuggestion(**s) for s in raw.get("suggestions", [])]
    return EnrichmentResponse(suggestions=suggestions, summary=raw.get("summary", ""))
