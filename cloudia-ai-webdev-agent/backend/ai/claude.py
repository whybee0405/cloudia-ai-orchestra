"""
Anthropic Claude API wrapper for the CloudIA agent system.

Provides singleton client, call_claude / call_claude_json helpers with
exponential backoff, token tracking, cost calculation, and structured logging.
NEVER logs full prompt text — client data privacy.
"""

import hashlib
import json
import re
import time
from typing import Any

import anthropic
import structlog

from backend.config import settings

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class ClaudeError(Exception):
    """Base exception for Claude API errors."""


class ClaudeJSONError(ClaudeError):
    """Raised when Claude's response cannot be parsed as JSON."""


class ClaudeRateLimitError(ClaudeError):
    """Raised when the Claude API returns a rate-limit response after all retries."""


# ---------------------------------------------------------------------------
# Pricing (Sonnet)
# ---------------------------------------------------------------------------

INPUT_COST_PER_TOKEN: float = 0.000003
OUTPUT_COST_PER_TOKEN: float = 0.000015

# ---------------------------------------------------------------------------
# Singleton client
# ---------------------------------------------------------------------------

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


# ---------------------------------------------------------------------------
# Retry helpers
# ---------------------------------------------------------------------------

_RETRY_DELAYS = (2, 4, 8)  # seconds


def _prompt_hash(prompt: str) -> str:
    """SHA-256 hex digest of a prompt — safe to log (no client data)."""
    return hashlib.sha256(prompt.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Core call
# ---------------------------------------------------------------------------


def call_claude(
    prompt: str,
    system: str = "",
    max_tokens: int = 4096,
) -> tuple[str, int, float]:
    """
    Call the Claude API and return (response_text, tokens_used, cost_usd).

    Retries up to 3 times with exponential backoff on rate-limit errors.
    Raises ClaudeRateLimitError if all retries are exhausted.
    Raises ClaudeError for other API failures.
    """
    client = _get_client()
    phash = _prompt_hash(prompt)

    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]

    last_exc: Exception | None = None
    for attempt, delay in enumerate([0] + list(_RETRY_DELAYS)):
        if delay:
            log.warning(
                "claude_retry",
                attempt=attempt,
                delay=delay,
                prompt_hash=phash,
            )
            time.sleep(delay)

        try:
            kwargs: dict[str, Any] = {
                "model": settings.anthropic_model,
                "max_tokens": max_tokens,
                "messages": messages,
            }
            if system:
                kwargs["system"] = system

            response = client.messages.create(**kwargs)

            input_tokens: int = response.usage.input_tokens
            output_tokens: int = response.usage.output_tokens
            total_tokens: int = input_tokens + output_tokens
            cost_usd: float = (
                input_tokens * INPUT_COST_PER_TOKEN
                + output_tokens * OUTPUT_COST_PER_TOKEN
            )

            response_text: str = response.content[0].text

            log.info(
                "claude_call",
                prompt_hash=phash,
                model=settings.anthropic_model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_usd=round(cost_usd, 6),
            )

            return response_text, total_tokens, cost_usd

        except anthropic.RateLimitError as exc:
            last_exc = exc
            log.warning("claude_rate_limit", attempt=attempt, prompt_hash=phash)
            if attempt == len(_RETRY_DELAYS):
                raise ClaudeRateLimitError(
                    f"Rate limit exceeded after {len(_RETRY_DELAYS) + 1} attempts"
                ) from exc
            continue

        except anthropic.APIError as exc:
            log.error("claude_api_error", error=str(exc), prompt_hash=phash)
            raise ClaudeError(f"Claude API error: {exc}") from exc

    # Should not reach here, but guard anyway
    raise ClaudeRateLimitError("Rate limit retries exhausted") from last_exc


# ---------------------------------------------------------------------------
# JSON-specific call
# ---------------------------------------------------------------------------

_MARKDOWN_CODE_BLOCK = re.compile(
    r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE
)


def _strip_markdown(text: str) -> str:
    """Remove markdown code fences, return raw content."""
    match = _MARKDOWN_CODE_BLOCK.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def call_claude_json(
    prompt: str,
    system: str = "",
    max_tokens: int = 4096,
) -> tuple[dict, int, float]:
    """
    Call Claude and parse the response as JSON.

    Returns (parsed_dict, tokens_used, cost_usd).
    Raises ClaudeJSONError if the response is not valid JSON.
    """
    text, tokens, cost = call_claude(prompt=prompt, system=system, max_tokens=max_tokens)
    cleaned = _strip_markdown(text)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        log.error(
            "claude_json_parse_error",
            prompt_hash=_prompt_hash(prompt),
            error=str(exc),
            # Log only first 200 chars of response — never the prompt
            response_preview=cleaned[:200],
        )
        raise ClaudeJSONError(
            f"Claude response is not valid JSON: {exc}\nResponse preview: {cleaned[:200]}"
        ) from exc

    if not isinstance(parsed, dict):
        raise ClaudeJSONError(
            f"Claude JSON response is not a dict (got {type(parsed).__name__})"
        )

    return parsed, tokens, cost
