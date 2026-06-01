"""Brand DNA Service client — fetches brand context for injection into Claude prompts."""
import json
import logging
import time
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

_cache: dict[str, tuple[str, float]] = {}
_TTL = 300  # 5 minutes — matches Claude prompt cache window


def get_brand_context_block(brand_dna_client_id: str) -> str:
    """Return the pre-formatted brand DNA prompt block for a client UUID.

    Returns empty string if the Brand DNA Service is unavailable or the client
    has no brand DNA configured — agents should handle this gracefully.
    """
    now = time.monotonic()
    cached = _cache.get(brand_dna_client_id)
    if cached and now < cached[1]:
        return cached[0]

    try:
        from backend.config import get_settings
        settings = get_settings()
        url = f"{settings.brand_dna_service_url}/internal/clients/{brand_dna_client_id}/brand-context"
        req = urllib.request.Request(
            url,
            headers={
                "X-Internal-Secret": settings.internal_api_secret or "",
                "X-Service-Name": "campaign-director",
            },
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            block: str = data.get("prompt_block", "")
            _cache[brand_dna_client_id] = (block, now + _TTL)
            logger.debug("Brand DNA loaded for client %s (%d chars)", brand_dna_client_id, len(block))
            return block
    except Exception as exc:
        logger.debug("Brand DNA unavailable for client %s: %s", brand_dna_client_id, exc)
        return ""
