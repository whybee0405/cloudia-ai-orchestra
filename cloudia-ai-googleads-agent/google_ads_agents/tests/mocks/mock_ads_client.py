"""Configurable mock for AdsClient — returns realistic GAQL rows without hitting the API."""

from typing import Any
from unittest.mock import MagicMock


class MockAdsRow:
    """Minimal fake of a proto-plus GoogleAdsRow for GAQL parsing tests."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        return _DotDict(self._data.get(name, {}))


class _DotDict:
    """Converts a nested dict to attribute access (mirrors proto-plus behaviour)."""

    def __init__(self, data: dict | Any) -> None:
        if isinstance(data, dict):
            self._data = data
        else:
            self._scalar = data
            self._data = {}

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        val = self._data.get(name)
        if isinstance(val, dict):
            return _DotDict(val)
        return val

    def __str__(self) -> str:
        return str(getattr(self, "_scalar", self._data))


def _make_campaign_row(
    campaign_id: str = "111222333",
    campaign_name: str = "Brand - Search",
    status: str = "ENABLED",
    impressions: int = 5000,
    clicks: int = 225,
    cost_micros: int = 4_500_000_000,
    conversions: float = 7.0,
    ctr: float = 0.045,
    avg_cpc: int = 20_000_000,
    cost_per_conversion: float = 642_857_143,
    conversion_rate: float = 0.031,
    search_impression_share: float = 0.65,
    budget_micros: int = 500_000_000,
) -> dict[str, Any]:
    return {
        "campaign": {
            "id": campaign_id,
            "name": campaign_name,
            "status": _NameObj(status),
        },
        "campaign_budget": {"amount_micros": budget_micros},
        "metrics": {
            "impressions": impressions,
            "clicks": clicks,
            "cost_micros": cost_micros,
            "conversions": conversions,
            "ctr": ctr,
            "average_cpc": avg_cpc,
            "cost_per_conversion": cost_per_conversion,
            "conversions_from_interactions_rate": conversion_rate,
            "search_impression_share": search_impression_share,
            "roas": 0,
        },
    }


class _NameObj:
    def __init__(self, name: str) -> None:
        self.name = name


class MockAdsClient:
    """Configurable mock that tracks calls and returns scenario-specific data."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self._scenario: str = "default"
        self._custom_return: dict[str, list] = {}

    def configure(self, scenario: str) -> "MockAdsClient":
        self._scenario = scenario
        return self

    def set_query_result(self, query: str, rows: list) -> "MockAdsClient":
        self._custom_return[query] = rows
        return self

    def run_query(self, customer_id: str, query: str) -> list:
        self.calls.append((customer_id, query))

        if query in self._custom_return:
            return self._custom_return[query]

        if self._scenario == "empty":
            return []

        if self._scenario == "ctr_drop":
            return [_make_campaign_row(ctr=0.025, impressions=5000, clicks=125)]

        if self._scenario == "high_spend":
            return [_make_campaign_row(cost_micros=50_000_000_000, clicks=1000)]

        if self._scenario == "zero_conversions":
            return [_make_campaign_row(conversions=0, clicks=250, cost_micros=5_000_000_000)]

        # default: normal healthy campaign
        return [_make_campaign_row()]

    def get_service(self, service_name: str) -> MagicMock:
        return MagicMock()

    def get_type(self, type_name: str) -> MagicMock:
        return MagicMock()

    @property
    def enums(self) -> MagicMock:
        return MagicMock()

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def was_called_with_query(self, query_fragment: str) -> bool:
        return any(query_fragment in q for _, q in self.calls)
