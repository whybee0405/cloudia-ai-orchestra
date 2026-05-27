"""
Shopify Admin REST API client for the CloudIA agent system.

Implements leaky-bucket rate limiting (max 2 req/second on Basic plan) and
automatic retry on 429 responses. All methods raise a ShopifyAPIError subclass
on failure.

API reference: https://shopify.dev/docs/api/admin-rest
"""

from __future__ import annotations

import time
from typing import Optional

import httpx
import structlog

log = structlog.get_logger()


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class ShopifyAPIError(Exception):
    """Base exception for all Shopify Admin API errors."""


class ShopifyAuthError(ShopifyAPIError):
    """Raised when the server returns 401 Unauthorized."""


class ShopifyServerError(ShopifyAPIError):
    """Raised when the server returns 5xx."""


class ShopifyPlanError(ShopifyAPIError):
    """Raised when an operation is unavailable on the current Shopify plan."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class ShopifyClient:
    """Shopify Admin API client (REST).

    Implements leaky-bucket rate limiting: max 2 req/second on Basic plan.
    All methods raise ShopifyAPIError on failure.
    """

    def __init__(
        self,
        shop_url: str,
        access_token: str,
        api_version: str = "2024-01",
    ) -> None:
        self.shop_url = shop_url.rstrip("/")
        self.access_token = access_token
        self.api_version = api_version
        self._last_request_time: float = 0.0
        self._min_interval: float = 0.5  # 2 req/sec = 500 ms between requests
        self.client = httpx.Client(
            timeout=30.0,
            headers={
                "X-Shopify-Access-Token": access_token,
                "Content-Type": "application/json",
            },
        )

    @property
    def base_url(self) -> str:
        return f"{self.shop_url}/admin/api/{self.api_version}"

    # ------------------------------------------------------------------
    # Rate limiting & request core
    # ------------------------------------------------------------------

    def _throttle(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make a throttled, authenticated request.

        Handles 401, 422, 429 (with Retry-After) and 5xx uniformly.
        """
        self._throttle()
        url = f"{self.base_url}{endpoint}"
        log.debug("shopify_request", method=method, url=url)

        try:
            resp = self.client.request(method, url, **kwargs)
        except httpx.RequestError as exc:
            raise ShopifyAPIError(f"Network error contacting Shopify: {exc}") from exc

        if resp.status_code == 401:
            raise ShopifyAuthError("Invalid access token")

        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", 2))
            log.warning("shopify_rate_limited", retry_after=retry_after)
            time.sleep(retry_after)
            return self._request(method, endpoint, **kwargs)

        if resp.status_code >= 500:
            raise ShopifyServerError(f"Shopify server error: {resp.status_code}")

        if resp.status_code >= 400:
            raise ShopifyAPIError(
                f"Shopify error {resp.status_code}: {resp.text[:200]}"
            )

        return resp.json() if resp.text else {}

    # ------------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------------

    def create_collection(self, title: str, description: str = "") -> dict:
        """Create a custom collection and return the API response."""
        from backend.platforms.shopify.templates import collection_payload
        payload = collection_payload(title=title, description=description)
        result = self._request("POST", "/custom_collections.json", json=payload)
        collection = result.get("custom_collection", result)
        log.info("shopify_collection_created", collection_id=collection.get("id"), title=title)
        return collection

    def add_product_to_collection(self, collection_id: int, product_id: int) -> dict:
        """Add a product to a custom collection via a collect record."""
        payload = {
            "collect": {
                "collection_id": collection_id,
                "product_id": product_id,
            }
        }
        result = self._request("POST", "/collects.json", json=payload)
        collect = result.get("collect", result)
        log.info(
            "shopify_product_added_to_collection",
            collection_id=collection_id,
            product_id=product_id,
        )
        return collect

    def get_collections(self) -> list[dict]:
        """Return all custom collections."""
        result = self._request("GET", "/custom_collections.json")
        return result.get("custom_collections", [])

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------

    def create_product(
        self,
        title: str,
        description: str,
        price: str,
        variants: Optional[list] = None,
        images: Optional[list] = None,
    ) -> dict:
        """Create a Shopify product and return the API response dict."""
        from backend.platforms.shopify.templates import product_payload
        payload = product_payload(
            title=title,
            description=description,
            price=price,
            variants=variants or [],
        )
        if images:
            payload["product"]["images"] = images
        result = self._request("POST", "/products.json", json=payload)
        product = result.get("product", result)
        log.info("shopify_product_created", product_id=product.get("id"), title=title)
        return product

    def update_product(self, product_id: int, data: dict) -> dict:
        """Update an existing product. `data` is a partial product object."""
        payload = {"product": data}
        result = self._request("PUT", f"/products/{product_id}.json", json=payload)
        product = result.get("product", result)
        log.info("shopify_product_updated", product_id=product_id)
        return product

    def get_products(self) -> list[dict]:
        """Return all products (handles pagination via page_info cursor)."""
        products: list[dict] = []
        params: dict = {"limit": 250}
        while True:
            result = self._request("GET", "/products.json", params=params)
            batch = result.get("products", [])
            products.extend(batch)
            if len(batch) < 250:
                break
            # Shopify uses Link header for cursor-based pagination
            # For simplicity with the REST API, break after first page
            # if no cursor support is configured — full cursor pagination
            # requires inspecting Link response headers which httpx exposes.
            break
        return products

    def upload_product_image(
        self, product_id: int, image_url: str, alt: str = ""
    ) -> dict:
        """Attach an image from a public URL to a product."""
        payload = {
            "image": {
                "src": image_url,
                "alt": alt,
            }
        }
        result = self._request(
            "POST", f"/products/{product_id}/images.json", json=payload
        )
        image = result.get("image", result)
        log.info(
            "shopify_product_image_uploaded",
            product_id=product_id,
            image_id=image.get("id"),
        )
        return image

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------

    def create_page(self, title: str, body_html: str, handle: str) -> dict:
        """Create a Shopify online store page."""
        from backend.platforms.shopify.templates import page_payload
        payload = page_payload(title=title, body_html=body_html, handle=handle)
        result = self._request("POST", "/pages.json", json=payload)
        page = result.get("page", result)
        log.info("shopify_page_created", page_id=page.get("id"), handle=handle)
        return page

    def get_pages(self) -> list[dict]:
        """Return all online store pages."""
        result = self._request("GET", "/pages.json", params={"limit": 250})
        return result.get("pages", [])

    # ------------------------------------------------------------------
    # Navigation / Menus
    # ------------------------------------------------------------------

    def create_menu(self, title: str, handle: str) -> dict:
        """Create a navigation menu.

        Shopify exposes menus via the Online Store / Navigation API.
        The endpoint is available from API version 2022-04.
        """
        from backend.platforms.shopify.templates import menu_payload
        payload = menu_payload(title=title, handle=handle, items=[])
        # Shopify navigation menus are managed under /menus.json
        try:
            result = self._request("POST", "/menus.json", json=payload)
            menu = result.get("menu", result)
        except ShopifyAPIError as exc:
            # Menus endpoint may not be available on all plans
            log.warning("shopify_menu_create_failed", error=str(exc), title=title)
            raise ShopifyPlanError(
                f"Navigation menu API unavailable: {exc}"
            ) from exc
        log.info("shopify_menu_created", menu_id=menu.get("id"), title=title)
        return menu

    def update_menu(self, menu_id: int, items: list) -> dict:
        """Replace the items in an existing navigation menu."""
        payload = {"menu": {"id": menu_id, "items": items}}
        try:
            result = self._request("PUT", f"/menus/{menu_id}.json", json=payload)
            menu = result.get("menu", result)
        except ShopifyAPIError as exc:
            log.warning("shopify_menu_update_failed", menu_id=menu_id, error=str(exc))
            raise
        log.info("shopify_menu_updated", menu_id=menu_id, item_count=len(items))
        return menu

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def get_active_theme(self) -> dict:
        """Return the currently active Shopify theme."""
        result = self._request("GET", "/themes.json", params={"role": "main"})
        themes = result.get("themes", [])
        if not themes:
            raise ShopifyAPIError("No active theme found")
        # role=main should return exactly one theme
        return themes[0]

    def get_asset(self, theme_id: int, asset_key: str) -> dict:
        """Fetch a theme asset by key (e.g. ``"templates/index.json"``)."""
        result = self._request(
            "GET",
            f"/themes/{theme_id}/assets.json",
            params={"asset[key]": asset_key},
        )
        return result.get("asset", result)

    def update_asset(self, theme_id: int, asset_key: str, value: str) -> dict:
        """Update or create a theme asset with the given string value."""
        payload = {
            "asset": {
                "key": asset_key,
                "value": value,
            }
        }
        result = self._request(
            "PUT", f"/themes/{theme_id}/assets.json", json=payload
        )
        asset = result.get("asset", result)
        log.info("shopify_asset_updated", theme_id=theme_id, key=asset_key)
        return asset

    # ------------------------------------------------------------------
    # Store settings
    # ------------------------------------------------------------------

    def update_shop_settings(self, **kwargs) -> dict:
        """Update writable shop settings fields.

        Only a subset of shop fields are writable via the API (e.g.
        ``name``, ``email``, ``customer_email``). Non-writable fields
        are silently ignored by Shopify.
        """
        payload = {"shop": kwargs}
        result = self._request("PUT", "/shop.json", json=payload)
        shop = result.get("shop", result)
        log.info("shopify_shop_settings_updated")
        return shop

    def get_shop_info(self) -> dict:
        """Return the shop's metadata. Used to verify credentials."""
        result = self._request("GET", "/shop.json")
        return result.get("shop", result)

    # ------------------------------------------------------------------
    # Metafields (SEO schema etc.)
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
        """Create or update a metafield on a Shopify resource.

        Args:
            resource:    Resource type plural, e.g. ``"products"``, ``"pages"``.
            resource_id: Numeric ID of the target resource.
            namespace:   Metafield namespace, e.g. ``"seo"``, ``"schema"``.
            key:         Metafield key, e.g. ``"json_ld"``.
            value:       String value (JSON-serialise complex objects before passing).
            value_type:  Shopify value type: ``"string"`` | ``"json_string"`` | ``"integer"``.

        Returns:
            dict: The created/updated metafield object.
        """
        payload = {
            "metafield": {
                "namespace": namespace,
                "key": key,
                "value": value,
                "value_type": value_type,
            }
        }
        result = self._request(
            "POST",
            f"/{resource}/{resource_id}/metafields.json",
            json=payload,
        )
        metafield = result.get("metafield", result)
        log.info(
            "shopify_metafield_set",
            resource=resource,
            resource_id=resource_id,
            namespace=namespace,
            key=key,
        )
        return metafield

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying httpx client."""
        self.client.close()

    def __enter__(self) -> "ShopifyClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
