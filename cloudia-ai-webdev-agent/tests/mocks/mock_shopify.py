"""
Mock Shopify Admin API client for the CloudIA test suite.

Provides:
  - MockShopifyClient — records calls, supports configurable failures
  - mock_shopify_client context manager — patches ShopifyClient constructor
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch

from backend.platforms.shopify.client import (
    ShopifyAPIError,
    ShopifyAuthError,
    ShopifyPlanError,
    ShopifyServerError,
)


# ---------------------------------------------------------------------------
# MockShopifyClient
# ---------------------------------------------------------------------------


class MockShopifyClient:
    """Configurable mock for ShopifyClient.

    Args:
        auth_fail:    Raise ShopifyAuthError on get_shop_info.
        rate_limited: Simulate a single 429 retry on the first create_product call.
        plan_error:   Raise ShopifyPlanError on create_menu.
    """

    def __init__(
        self,
        auth_fail: bool = False,
        rate_limited: bool = False,
        plan_error: bool = False,
    ) -> None:
        self.auth_fail = auth_fail
        self.rate_limited = rate_limited
        self.plan_error = plan_error
        self.calls: list[tuple] = []
        self._id_counter = 0
        self._rate_limit_triggered = False

    def _next_id(self) -> int:
        self._id_counter += 1
        return self._id_counter

    # ------------------------------------------------------------------
    # Shop info / verification
    # ------------------------------------------------------------------

    def get_shop_info(self) -> dict:
        self.calls.append(("get_shop_info",))
        if self.auth_fail:
            raise ShopifyAuthError("Invalid access token — 401")
        return {
            "id": 1,
            "name": "Test Store",
            "currency": "ZAR",
            "domain": "test.myshopify.com",
            "plan_name": "basic",
        }

    # ------------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------------

    def create_collection(self, title: str, description: str = "") -> dict:
        self.calls.append(("create_collection", title))
        coll_id = self._next_id()
        return {
            "id": coll_id,
            "title": title,
            "handle": title.lower().replace(" ", "-"),
        }

    def get_collections(self) -> list[dict]:
        self.calls.append(("get_collections",))
        return []

    def add_product_to_collection(self, collection_id: int, product_id: int) -> dict:
        self.calls.append(("add_product_to_collection", collection_id, product_id))
        return {"collection_id": collection_id, "product_id": product_id}

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------

    def create_product(
        self,
        title: str,
        description: str,
        price: str,
        variants: list | None = None,
        images: list | None = None,
    ) -> dict:
        self.calls.append(("create_product", title, price))

        # Rate-limit simulation: raise on first call if configured
        if self.rate_limited and not self._rate_limit_triggered:
            self._rate_limit_triggered = True
            raise ShopifyAPIError("429 Too Many Requests")

        # Validate price
        try:
            price_val = float(price)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid price value: {price!r}")

        if price_val == 0:
            raise ValueError("Product price cannot be R0.00 — Shopify will reject this")

        return {
            "id": self._next_id(),
            "title": title,
            "status": "active",
            "variants": [{"price": price}],
        }

    def update_product(self, product_id: int, data: dict) -> dict:
        self.calls.append(("update_product", product_id))
        return {"id": product_id, **data}

    def upload_product_image(self, product_id: int, image_url: str, alt: str = "") -> dict:
        self.calls.append(("upload_product_image", product_id))
        return {"id": self._next_id(), "src": image_url, "alt": alt}

    def get_products(self) -> list[dict]:
        self.calls.append(("get_products",))
        return []

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------

    def create_page(self, title: str, body_html: str, handle: str) -> dict:
        self.calls.append(("create_page", title, handle))
        return {"id": self._next_id(), "title": title, "handle": handle}

    def get_pages(self) -> list[dict]:
        self.calls.append(("get_pages",))
        return []

    # ------------------------------------------------------------------
    # Navigation / menus
    # ------------------------------------------------------------------

    def create_menu(self, title: str, handle: str) -> dict:
        self.calls.append(("create_menu", title, handle))
        if self.plan_error:
            raise ShopifyPlanError("Navigation menu API unavailable on this plan")
        return {"id": self._next_id(), "title": title, "handle": handle}

    def update_menu(self, menu_id: int, items: list) -> dict:
        self.calls.append(("update_menu", menu_id))
        return {"id": menu_id, "items": items}

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def get_active_theme(self) -> dict:
        self.calls.append(("get_active_theme",))
        return {"id": 1, "name": "Dawn", "role": "main"}

    def get_asset(self, theme_id: int, asset_key: str) -> dict:
        self.calls.append(("get_asset", theme_id, asset_key))
        return {"key": asset_key, "value": '{"colors": {}}'}

    def update_asset(self, theme_id: int, asset_key: str, value: str) -> dict:
        self.calls.append(("update_asset", theme_id, asset_key))
        return {"key": asset_key, "value": value}

    # ------------------------------------------------------------------
    # Shop settings
    # ------------------------------------------------------------------

    def update_shop_settings(self, **kwargs) -> dict:
        self.calls.append(("update_shop_settings", kwargs))
        return {"name": kwargs.get("name", "Test Store")}

    # ------------------------------------------------------------------
    # Metafields
    # ------------------------------------------------------------------

    def set_metafield(
        self,
        resource: str,
        resource_id: int,
        namespace: str,
        key: str,
        value: str,
        value_type: str = "json_string",
    ) -> dict:
        self.calls.append(("set_metafield", resource, resource_id, namespace, key))
        return {
            "id": self._next_id(),
            "namespace": namespace,
            "key": key,
            "value": value,
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        self.calls.append(("close",))

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


@contextmanager
def mock_shopify_client(**kwargs):
    """Patch ShopifyClient to return a MockShopifyClient.

    Usage::

        with mock_shopify_client(auth_fail=True) as mock:
            # code under test
            ...
        assert any(c[0] == "get_shop_info" for c in mock.calls)
    """
    mock = MockShopifyClient(**kwargs)
    with patch(
        "backend.platforms.shopify.client.ShopifyClient",
        return_value=mock,
    ):
        yield mock
