"""OpenAI DALL-E 3 wrapper with Replicate (Flux) fallback."""
import logging
import httpx
from typing import Optional
from openai import OpenAI, BadRequestError, RateLimitError

from backend.config import get_settings

logger = logging.getLogger(__name__)
_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=get_settings().openai_api_key)
    return _client


def generate_image(prompt: str, size: str = "1024x1024", quality: str = "standard") -> tuple[bytes, str, float]:
    """
    Generate image with DALL-E 3. Falls back to Replicate Flux on failure.
    Returns (image_bytes, model_used, cost_usd).
    """
    try:
        return _dalle_generate(prompt, size, quality)
    except (BadRequestError, RateLimitError, Exception) as exc:
        logger.warning("DALL-E 3 failed (%s), falling back to Replicate Flux", exc)
        return _flux_generate(prompt)


def _dalle_generate(prompt: str, size: str, quality: str) -> tuple[bytes, str, float]:
    response = get_client().images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,
        quality=quality,
        n=1,
        response_format="url",
    )
    url = response.data[0].url
    image_bytes = httpx.get(url, timeout=60).content
    cost = 0.04 if quality == "standard" else 0.08
    logger.debug("DALL-E 3 image generated, size=%d bytes, cost=$%.4f", len(image_bytes), cost)
    return image_bytes, "dall-e-3", cost


def _flux_generate(prompt: str) -> tuple[bytes, str, float]:
    from backend.ai.replicate_client import generate_image as replicate_generate
    return replicate_generate(prompt)
