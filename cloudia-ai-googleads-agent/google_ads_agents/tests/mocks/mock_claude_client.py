"""Configurable mock for ClaudeClient — returns realistic JSON per agent type."""

import json
from typing import Any


class MockClaudeClient:
    """Tracks prompts and returns configurable responses per agent type."""

    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []
        self._mode: str = "valid"
        self._agent_responses: dict[str, Any] = {}

    def configure(self, mode: str) -> "MockClaudeClient":
        """mode: 'valid' | 'malformed_json' | 'empty' | 'exception'"""
        self._mode = mode
        return self

    def set_response(self, agent: str, response: dict[str, Any]) -> "MockClaudeClient":
        self._agent_responses[agent] = response
        return self

    def complete(self, system_prompt: str, user_message: str, max_tokens: int | None = None) -> tuple[str, int]:
        self.calls.append({"system": system_prompt[:50], "user": user_message[:100]})

        if self._mode == "exception":
            raise ConnectionError("Simulated network failure")
        if self._mode == "empty":
            return "", 0

        return json.dumps(self._get_default_response(system_prompt)), 500

    def complete_json(self, system_prompt: str, user_message: str, max_tokens: int | None = None) -> tuple[Any, int]:
        self.calls.append({"system": system_prompt[:50], "user": user_message[:100]})

        if self._mode == "exception":
            raise ConnectionError("Simulated network failure")
        if self._mode == "empty":
            raise ValueError("Claude returned non-JSON: ")
        if self._mode == "malformed_json":
            raise ValueError("Claude returned non-JSON: Expecting value")

        # Check for specific agent responses
        for agent_key, response in self._agent_responses.items():
            if agent_key in system_prompt.lower() or agent_key in user_message.lower():
                return response, 500

        return self._get_default_response(system_prompt), 500

    def _get_default_response(self, system_prompt: str) -> Any:
        prompt_lower = system_prompt.lower()

        if "auditor" in prompt_lower or "anomaly" in prompt_lower:
            return {
                "anomaly_type": "ctr_drop",
                "severity": "MEDIUM",
                "diagnosis": "CTR dropped 31% versus prior snapshot.",
                "recommended_action": "Review ad copy freshness and landing page relevance.",
            }

        if "manager" in prompt_lower or "bid" in prompt_lower or "budget" in prompt_lower:
            return {
                "decisions": [
                    {
                        "action_type": "increase_bid",
                        "target_id": "444555666",
                        "target_name": "Brand Ad Group",
                        "current_value": 15_000_000,
                        "recommended_value": 17_000_000,
                        "reasoning": "CTR above baseline — bid up to capture more volume.",
                    }
                ]
            }

        if "reporter" in prompt_lower or "report" in prompt_lower:
            return {
                "executive_summary": "Account performed within KPI targets this week.",
                "key_wins": ["CTR up 5%", "CPL below target"],
                "areas_of_concern": ["One campaign with zero conversions"],
                "top_campaigns": [{"name": "Brand", "spend": "R4,500", "conversions": 7}],
                "recommendations": ["Increase budget on Brand campaign by 10%"],
            }

        if "keyword" in prompt_lower or "scout" in prompt_lower:
            return {
                "new_keyword_opportunities": [
                    {
                        "keyword_text": "emergency dentist cape town",
                        "match_type": "PHRASE",
                        "ad_group_id": "444555666",
                        "reasoning": "High-intent search term with 45 clicks, zero conversions capture.",
                    }
                ],
                "negatives_to_add": [],
                "match_type_adjustments": [],
            }

        if "creator" in prompt_lower or "campaign structure" in prompt_lower:
            return {
                "campaign_name": "Test Campaign - Brand",
                "campaign_settings": {
                    "budget_daily_micros": 200_000_000,
                    "bidding_strategy": "MANUAL_CPC",
                    "network_settings": {"search": True, "display": False},
                },
                "ad_groups": [
                    {
                        "name": "Brand Terms",
                        "cpc_bid_micros": 20_000_000,
                        "keywords": [{"text": "test brand", "match_type": "EXACT"}],
                        "ads": [
                            {
                                "headlines": ["Test Brand", "Quality Service", "Book Today"],
                                "descriptions": ["Reliable service in Cape Town.", "Call now for a free quote."],
                                "final_url": "https://example.co.za",
                            }
                        ],
                    }
                ],
            }

        return {}

    @staticmethod
    def estimate_cost_usd(tokens_used: int) -> float:
        return round(tokens_used * 6 / 1_000_000, 6)

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def was_called(self) -> bool:
        return len(self.calls) > 0
