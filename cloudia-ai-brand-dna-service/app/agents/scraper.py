"""Website scraper — extracts structured brand signals for the setup flow."""
import logging
from typing import Optional
from pydantic import BaseModel

import httpx
from bs4 import BeautifulSoup

from app.agents.claude_client import ClaudeClient

logger = logging.getLogger(__name__)

_SYSTEM = """You are a brand analyst. Given a business name and their website text, extract brand signals.
Return ONLY valid JSON:
{
  "description": "2-3 sentence business description written in third person",
  "tagline_hint": "a potential tagline or actual tagline found on the site (empty string if none)",
  "tone_signals": ["descriptor1", "descriptor2"],
  "key_phrases": ["notable brand phrase or USP 1", "phrase 2", "phrase 3"],
  "suggested_prompt": "A ready-to-use 3-4 sentence description for brand DNA generation covering: what they do, who they serve, their market position, and what makes them different. Write it in first person as if the owner is speaking."
}"""


class ScrapeSignals(BaseModel):
    description: str
    tagline_hint: str
    tone_signals: list[str]
    key_phrases: list[str]
    suggested_prompt: str


def _fetch_text(url: str) -> str:
    try:
        with httpx.Client(timeout=12, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": "CloudIA BrandBot/1.0"})
            resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)[:4000]
    except Exception as exc:
        logger.warning("Scrape failed for %s: %s", url, exc)
        return ""


def scrape_brand_signals(business_name: str, website_url: str) -> Optional[ScrapeSignals]:
    text = _fetch_text(website_url)
    if not text:
        return None

    prompt = f"Business Name: {business_name}\nWebsite: {website_url}\n\n---\n{text}"
    try:
        raw = ClaudeClient().call_json(_SYSTEM, prompt, max_tokens=800)
        return ScrapeSignals(**raw)
    except Exception as exc:
        logger.warning("Scraper Claude call failed: %s", exc)
        return None
