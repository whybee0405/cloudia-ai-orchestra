"""Thin wrapper around the Anthropic SDK with token tracking and JSON extraction."""
import json
import logging
import re
from typing import Any

import anthropic

from app.config import get_settings

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> Any:
    """Pull the first JSON object or array out of a Claude response."""
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return json.loads(match.group(1).strip())
    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if match:
        return json.loads(match.group(1))
    raise ValueError(f"No JSON found in response: {text[:200]}")


class ClaudeClient:
    def __init__(self):
        settings = get_settings()
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model
        self.last_input_tokens = 0
        self.last_output_tokens = 0
        self.last_cost_usd = 0.0

    def call(self, system: str, user: str, max_tokens: int = 2048) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        self.last_input_tokens = response.usage.input_tokens
        self.last_output_tokens = response.usage.output_tokens
        # Sonnet 4.6 pricing: $3/MTok in, $15/MTok out
        self.last_cost_usd = (
            self.last_input_tokens * 3 / 1_000_000
            + self.last_output_tokens * 15 / 1_000_000
        )
        text = response.content[0].text
        logger.debug(
            "Claude call: in=%d out=%d cost=$%.6f",
            self.last_input_tokens, self.last_output_tokens, self.last_cost_usd,
        )
        return text

    def call_json(self, system: str, user: str, max_tokens: int = 2048) -> Any:
        text = self.call(system, user, max_tokens)
        return _extract_json(text)
