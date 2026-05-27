"""Anthropic API wrapper. All Claude calls go through here — never directly from agents."""

import logging
from typing import Any

import anthropic

import config

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Thin wrapper around the Anthropic client.

    Centralises model configuration, token tracking, and error handling.
    """

    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.model = config.ANTHROPIC_MODEL
        self.max_tokens = config.ANTHROPIC_MAX_TOKENS
        logger.info("ClaudeClient initialised (model: %s)", self.model)

    def complete(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int | None = None,
    ) -> tuple[str, int]:
        """Send a message to Claude and return the response text and tokens used.

        Args:
            system_prompt: The system prompt defining Claude's role.
            user_message: The user turn containing data and instructions.
            max_tokens: Override the default max token limit.

        Returns:
            Tuple of (response_text, total_tokens_used).
        """
        response = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens or self.max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        text = response.content[0].text
        tokens = response.usage.input_tokens + response.usage.output_tokens

        logger.debug(
            "Claude response: %d tokens (in=%d, out=%d)",
            tokens,
            response.usage.input_tokens,
            response.usage.output_tokens,
        )
        return text, tokens

    def complete_json(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int | None = None,
    ) -> tuple[Any, int]:
        """Call Claude and parse the response as JSON.

        Wraps complete() and deserialises the JSON payload.

        Returns:
            Tuple of (parsed_object, total_tokens_used).

        Raises:
            ValueError: If the response cannot be parsed as JSON.
        """
        import json
        import re

        text, tokens = self.complete(
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=max_tokens,
        )

        # Strip markdown code fences if Claude wraps the JSON
        clean = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
        clean = re.sub(r"```\s*$", "", clean.strip(), flags=re.MULTILINE)

        try:
            return json.loads(clean.strip()), tokens
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse Claude JSON response: %s\nRaw: %s", exc, text[:500])
            raise ValueError(f"Claude returned non-JSON: {exc}") from exc

    @staticmethod
    def estimate_cost_usd(tokens_used: int) -> float:
        """Rough cost estimate in USD for Sonnet (blended input/output rate)."""
        # claude-sonnet-4: ~$3 per 1M input, ~$15 per 1M output — blended ~$6/1M
        return round(tokens_used * 6 / 1_000_000, 6)
