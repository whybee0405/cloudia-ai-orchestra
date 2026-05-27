"""Replicate Flux image generation — fallback for DALL-E 3."""
import logging
import httpx
import replicate

from backend.config import get_settings

logger = logging.getLogger(__name__)

FLUX_MODEL = "black-forest-labs/flux-schnell"


def generate_image(prompt: str) -> tuple[bytes, str, float]:
    """Generate image via Replicate Flux. Returns (image_bytes, model_used, cost_usd)."""
    settings = get_settings()
    client = replicate.Client(api_token=settings.replicate_api_token)

    output = client.run(
        FLUX_MODEL,
        input={"prompt": prompt, "num_outputs": 1, "aspect_ratio": "1:1"},
    )
    url = str(output[0])
    image_bytes = httpx.get(url, timeout=120).content
    cost = 0.003  # Flux Schnell approximate cost
    logger.debug("Flux image generated, size=%d bytes", len(image_bytes))
    return image_bytes, "flux-schnell", cost
