"""Mock Claude AI client for testing."""
import json
from unittest.mock import MagicMock


class MockClaude:
    """
    Configurable mock for backend.ai.claude.call() and call_json().
    Tracks all calls to assert context was injected and correct model used.
    """

    def __init__(self, default_response="Mock Claude response"):
        self.calls = []
        self.default_response = default_response
        self._mode = "valid"  # valid | malformed_json | empty | timeout | rate_limit

    def set_mode(self, mode: str):
        self._mode = mode

    def call(self, system: str, user: str, model: str = None, cache_system: bool = False):
        self.calls.append({"system": system, "user": user, "model": model})

        if self._mode == "timeout":
            raise TimeoutError("Claude request timed out")
        if self._mode == "rate_limit":
            from anthropic import RateLimitError
            raise RateLimitError("Rate limit exceeded", response=MagicMock(), body={})
        if self._mode == "empty":
            return ("", 0, 0, 0.0)

        return (self.default_response, 100, 50, 0.003)

    def call_json(self, system: str, user: str, model: str = None, cache_system: bool = False):
        self.calls.append({"system": system, "user": user, "model": model})

        if self._mode == "malformed_json":
            return ({"error": "This is not valid JSON but returned as empty dict"}, 0, 0, 0.0)
        if self._mode == "timeout":
            raise TimeoutError("Claude request timed out")
        if self._mode == "empty":
            return ({}, 0, 0, 0.0)

        result = json.loads(self.default_response) if isinstance(self.default_response, str) else self.default_response
        return (result, 100, 50, 0.003)

    def assert_context_injected(self, expected_fragment: str):
        """Assert that expected_fragment appeared in at least one system prompt."""
        for call in self.calls:
            if expected_fragment in call.get("system", ""):
                return True
        raise AssertionError(
            f"Expected '{expected_fragment}' in Claude system prompt, but got:\n"
            + "\n---\n".join(c.get("system", "")[:200] for c in self.calls)
        )

    def assert_model_used(self, expected_model: str):
        for call in self.calls:
            if call.get("model") == expected_model:
                return True
        raise AssertionError(
            f"Expected model '{expected_model}', got: {[c.get('model') for c in self.calls]}"
        )

    def reset(self):
        self.calls = []
        self._mode = "valid"


# Planner expects claude.call_json to return a LIST directly (not {"calendar": [...]})
CALENDAR_JSON_RESPONSE = json.dumps([
    {
        "platform": "instagram",
        "content_type": "image_post",
        "scheduled_for": "2026-06-01T09:00:00",
        "notes": "Feature Korean car parts",
    },
    {
        "platform": "facebook",
        "content_type": "image_post",
        "scheduled_for": "2026-06-02T10:00:00",
        "notes": "Winter service promo",
    },
    {
        "platform": "instagram",
        "content_type": "reel",
        "scheduled_for": "2026-06-03T19:00:00",
        "notes": "Behind the scenes reel",
    },
])

CAPTION_RESPONSE = (
    "Upgrade your Korean car this winter with same-day delivery from Sandton Auto Spares. "
    "Fast, reliable, professional. Book your service today! #sandtonauto #koreancarparts"
)

VIDEO_SCRIPT_RESPONSE = json.dumps({
    "total_duration_sec": 30,
    "scenes": [
        {
            "duration_sec": 10,
            "visual": "Mechanic changing Korean car parts",
            "voiceover": "Sandton Auto Spares delivers Korean car parts same-day.",
            "text_overlay": "Same-Day Delivery",
        },
        {
            "duration_sec": 10,
            "visual": "Happy customer receiving parts",
            "voiceover": "Professional service you can trust.",
            "text_overlay": "Professional & Reliable",
        },
        {
            "duration_sec": 10,
            "visual": "Sandton Auto Spares storefront",
            "voiceover": "Book your service today.",
            "text_overlay": "Book Today",
        },
    ],
})
