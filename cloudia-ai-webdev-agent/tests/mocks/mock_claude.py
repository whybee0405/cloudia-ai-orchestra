"""
Mock Claude API module for the CloudIA test suite.

Provides:
  - Realistic per-agent response payloads (DIRECTOR_RESPONSE, CONTENT_RESPONSE, etc.)
  - MockClaude class — records all calls, configurable for errors and malformed JSON
  - mock_claude_module context manager — patches backend.ai.claude functions
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Realistic response payloads
# ---------------------------------------------------------------------------

CONTENT_RESPONSE = {
    "home": {
        "title": "Sandton Dental Studio — Expert Dentistry",
        "h1": "Comprehensive Dental Care in the Heart of Sandton",
        "body_content": (
            "Welcome to Sandton Dental Studio, where exceptional dental care meets patient "
            "comfort. Our experienced team provides everything from routine check-ups to "
            "advanced cosmetic procedures. We proudly serve Sandton and the greater "
            "Johannesburg area with same-day emergency appointments and transparent pricing "
            "that ensures you know exactly what you are paying before treatment begins."
        ),
        "cta_text": "Book Your Appointment Today",
        "meta_title": "Sandton Dental Studio — Expert Dentistry",
        "meta_description": (
            "Expert dental care in Sandton. Same-day emergencies. "
            "Transparent pricing. Book your appointment online today."
        ),
    }
}

DIRECTOR_RESPONSE = {
    "platform": "wordpress",
    "reasoning": "Dental clinic is a local service business without ecommerce requirements.",
    "estimated_pages": 4,
    "page_list": ["home", "about", "services", "contact"],
    "requires_woocommerce": False,
    "requires_blog": False,
    "content_requirements": {},
}

DIRECTOR_SHOPIFY_RESPONSE = {
    "platform": "shopify",
    "reasoning": "Business sells products online and requires cart, inventory and checkout.",
    "estimated_pages": 4,
    "page_list": ["home", "about", "contact", "faq"],
    "requires_woocommerce": False,
    "requires_blog": False,
    "content_requirements": {},
}

DIRECTOR_AMBIGUOUS_RESPONSE = {
    "platform": "ambiguous",
    "reasoning": "Brief does not clarify if the business sells products online.",
    "ambiguity_reason": "Could not determine if ecommerce is required from the brief.",
    "estimated_pages": 0,
    "page_list": [],
}

SEO_RESPONSE = {
    "meta_title": "Sandton Dental Studio — Cosmetic & General Dentistry",
    "meta_description": (
        "Expert dental care in Sandton. Same-day emergency appointments. "
        "Transparent pricing. Book your appointment online today."
    ),
    "schema": {
        "@context": "https://schema.org",
        "@type": "Dentist",
        "name": "Sandton Dental Studio",
        "address": {
            "@type": "PostalAddress",
            "addressLocality": "Sandton",
            "addressCountry": "ZA",
        },
    },
    "sitemap_urls": [
        "https://test.sandtondental.co.za/",
        "https://test.sandtondental.co.za/about/",
        "https://test.sandtondental.co.za/services/",
        "https://test.sandtondental.co.za/contact/",
    ],
}


# ---------------------------------------------------------------------------
# MockClaude class
# ---------------------------------------------------------------------------


class MockClaude:
    """Configurable mock for Claude API calls.

    Records all calls in ``self.calls`` for assertion in tests.
    """

    def __init__(
        self,
        response: object = None,
        raise_error: Exception | None = None,
        malformed_json: bool = False,
    ):
        self.response = response if response is not None else CONTENT_RESPONSE
        self.raise_error = raise_error
        self.malformed_json = malformed_json
        self.calls: list[dict] = []

    def call_claude(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 4096,
    ) -> tuple[str, int, float]:
        """Mock for backend.ai.claude.call_claude."""
        self.calls.append({"fn": "call_claude", "prompt": prompt, "system": system})
        if self.raise_error:
            raise self.raise_error
        if self.malformed_json:
            return "This is not JSON {{{broken", 100, 0.001
        return json.dumps(self.response), 100, 0.001

    def call_claude_json(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 4096,
    ) -> tuple[dict, int, float]:
        """Mock for backend.ai.claude.call_claude_json."""
        self.calls.append({"fn": "call_claude_json", "prompt": prompt, "system": system})
        if self.raise_error:
            raise self.raise_error
        if self.malformed_json:
            from backend.ai.claude import ClaudeJSONError

            raise ClaudeJSONError("Response was not valid JSON")
        return self.response, 100, 0.001


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


@contextmanager
def mock_claude_module(
    response: object = None,
    raise_error: Exception | None = None,
    malformed_json: bool = False,
):
    """Patch backend.ai.claude functions for the duration of the with-block.

    Usage::

        with mock_claude_module(response=DIRECTOR_RESPONSE) as mock:
            result = director.analyze()
        assert len(mock.calls) > 0
    """
    mock = MockClaude(
        response=response,
        raise_error=raise_error,
        malformed_json=malformed_json,
    )
    with (
        patch("backend.ai.claude.call_claude", side_effect=mock.call_claude),
        patch("backend.ai.claude.call_claude_json", side_effect=mock.call_claude_json),
    ):
        yield mock
