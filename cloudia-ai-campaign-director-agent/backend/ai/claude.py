"""Anthropic Claude wrapper — all Claude calls go through this module."""
import logging
import threading
import time
from typing import Optional
import anthropic

from backend.config import get_settings

logger = logging.getLogger(__name__)
_client: Optional[anthropic.Anthropic] = None

# Thread-local brand context — set once per Celery task, auto-prepended to every system prompt
_brand_ctx = threading.local()


def set_brand_context(block: str) -> None:
    """Set the brand DNA block for the current thread (Celery task)."""
    _brand_ctx.block = block


def clear_brand_context() -> None:
    _brand_ctx.block = ""


def _get_brand_context() -> str:
    return getattr(_brand_ctx, "block", "")


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=get_settings().anthropic_api_key)
    return _client


def call(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    cache_system: bool = True,
) -> tuple[str, int, int, float]:
    """
    Call Claude and return (text, input_tokens, output_tokens, cost_usd).

    Uses prompt caching on the system prompt when cache_system=True.
    """
    settings = get_settings()
    model = model or settings.anthropic_model

    # Prepend brand DNA block if available for this thread (Celery task)
    brand_block = _get_brand_context()
    if brand_block:
        system_prompt = brand_block + "\n\n" + system_prompt

    system: list[dict] = []
    if cache_system:
        system = [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]
    else:
        system = [{"type": "text", "text": system_prompt}]

    start = time.monotonic()
    response = get_client().messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )
    elapsed = time.monotonic() - start

    text = response.content[0].text
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    # Cost estimate — Sonnet pricing (update if model changes)
    cost_usd = (input_tokens / 1_000_000 * 3.0) + (output_tokens / 1_000_000 * 15.0)

    logger.debug(
        "Claude call: model=%s tokens_in=%d tokens_out=%d cost=$%.6f elapsed=%.2fs",
        model, input_tokens, output_tokens, cost_usd, elapsed,
    )
    return text, input_tokens, output_tokens, cost_usd


def call_json(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    max_tokens: int = 4096,
) -> tuple[dict | list, int, int, float]:
    """Call Claude expecting valid JSON back. Strips any markdown fences."""
    import json
    text, inp, out, cost = call(
        system_prompt,
        user_prompt + "\n\nReturn ONLY valid JSON. No markdown, no preamble.",
        model=model,
        max_tokens=max_tokens,
        temperature=0.3,
    )
    # Strip markdown code fences if present
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return json.loads(cleaned), inp, out, cost
