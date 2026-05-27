"""
WordPress REST API client for the CloudIA agent system.

Uses WP Application Passwords for authentication (HTTP Basic with username + app password).
All public methods raise a WordPressAPIError subclass on failure — callers should not
need to inspect raw HTTP responses.

Endpoint base: <site_url>/wp-json/wp/v2
WooCommerce:   <site_url>/wp-json/wc/v3
Yoast SEO:     <site_url>/wp-json/yoast/v1
"""

from __future__ import annotations

import mimetypes
import os
from typing import Optional

import httpx
import structlog

log = structlog.get_logger()


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class WordPressAPIError(Exception):
    """Base exception for all WordPress REST API errors."""


class WordPressAuthError(WordPressAPIError):
    """Raised when the server returns 401 Unauthorized."""


class WordPressNotFoundError(WordPressAPIError):
    """Raised when the server returns 404 Not Found."""


class WordPressServerError(WordPressAPIError):
    """Raised when the server returns 5xx."""


class WordPressMaintenanceError(WordPressAPIError):
    """Raised when the site returns HTML instead of JSON (maintenance mode)."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class WordPressClient:
    """WordPress REST API client.

    Uses WP Application Passwords for auth (not username/password).
    All methods raise WordPressAPIError on non-2xx responses.
    """

    def __init__(self, site_url: str, username: str, app_password: str) -> None:
        # Normalize site_url: strip trailing slash, ensure /wp-json not doubled
        self.base_url = self._normalize_url(site_url)
        self.auth = (username, app_password)
        self.client = httpx.Client(timeout=30.0, auth=self.auth)

    def _normalize_url(self, url: str) -> str:
        url = url.rstrip("/")
        if url.endswith("/wp-json"):
            url = url[:-8]
        return url

    @property
    def api_url(self) -> str:
        return f"{self.base_url}/wp-json/wp/v2"

    @property
    def wc_url(self) -> str:
        return f"{self.base_url}/wp-json/wc/v3"

    # ------------------------------------------------------------------
    # Internal request helper
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        url: str,
        *,
        json: Optional[dict] = None,
        data: Optional[dict] = None,
        files: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """Execute an HTTP request and handle error responses uniformly."""
        log.debug("wp_request", method=method, url=url)
        try:
            resp = self.client.request(
                method,
                url,
                json=json,
                data=data,
                files=files,
                params=params,
            )
        except httpx.RequestError as exc:
            raise WordPressAPIError(f"Network error contacting WordPress: {exc}") from exc

        # Maintenance mode check — WordPress returns HTML when in maintenance
        content_type = resp.headers.get("content-type", "")
        if "text/html" in content_type and resp.status_code != 200:
            raise WordPressMaintenanceError(
                "Site in maintenance mode — received HTML"
            )

        if resp.status_code == 401:
            raise WordPressAuthError("Invalid credentials")
        if resp.status_code == 404:
            raise WordPressNotFoundError(f"Resource not found: {url}")
        if resp.status_code >= 500:
            raise WordPressServerError(
                f"WordPress server error {resp.status_code}: {resp.text[:200]}"
            )
        if resp.status_code >= 400:
            raise WordPressAPIError(
                f"WordPress API error {resp.status_code}: {resp.text[:200]}"
            )

        # Some endpoints return empty body on success (e.g. DELETE)
        if not resp.text:
            return {}
        return resp.json()

    def _get(self, endpoint: str, params: Optional[dict] = None) -> dict | list:
        return self._request("GET", endpoint, params=params)

    def _post(self, endpoint: str, json: Optional[dict] = None, data: Optional[dict] = None,
              files: Optional[dict] = None) -> dict:
        return self._request("POST", endpoint, json=json, data=data, files=files)

    def _put(self, endpoint: str, json: Optional[dict] = None) -> dict:
        return self._request("PUT", endpoint, json=json)

    def _patch(self, endpoint: str, json: Optional[dict] = None) -> dict:
        return self._request("PATCH", endpoint, json=json)

    def _delete(self, endpoint: str) -> dict:
        return self._request("DELETE", endpoint)

    # ------------------------------------------------------------------
    # Connection verification
    # ------------------------------------------------------------------

    def verify_connection(self) -> bool:
        """Check REST API is accessible. Raises WordPressAPIError if not."""
        url = f"{self.base_url}/wp-json/"
        resp_data = self._request("GET", url)
        # A valid WP JSON root always includes a 'namespaces' key
        if "namespaces" not in resp_data:
            raise WordPressAPIError(
                "Unexpected response from WordPress REST API root — may not be a WP site"
            )
        log.info("wp_connection_verified", site=self.base_url)
        return True

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------

    def create_page(
        self,
        title: str,
        content: str,
        slug: str,
        status: str = "draft",
        template: str = "",
        parent_id: int = 0,
    ) -> dict:
        """Create a WordPress page and return the API response dict."""
        from backend.platforms.wordpress.templates import page_payload
        payload = page_payload(
            title=title,
            content=content,
            slug=slug,
            status=status,
            template=template,
            parent_id=parent_id,
        )
        result = self._post(f"{self.api_url}/pages", json=payload)
        log.info("wp_page_created", page_id=result.get("id"), slug=slug)
        return result

    def update_page(self, page_id: int, data: dict) -> dict:
        """Update an existing page by ID. `data` is a partial WP page object."""
        result = self._post(f"{self.api_url}/pages/{page_id}", json=data)
        log.info("wp_page_updated", page_id=page_id)
        return result

    def get_page(self, page_id: int) -> dict:
        """Fetch a single page by ID."""
        return self._get(f"{self.api_url}/pages/{page_id}")

    def get_all_pages(self) -> list[dict]:
        """Return all pages (handles WordPress pagination up to 100 per page)."""
        pages: list[dict] = []
        page_num = 1
        while True:
            batch = self._get(
                f"{self.api_url}/pages",
                params={"per_page": 100, "page": page_num},
            )
            if not isinstance(batch, list) or not batch:
                break
            pages.extend(batch)
            if len(batch) < 100:
                break
            page_num += 1
        return pages

    def set_featured_image(self, page_id: int, media_id: int) -> dict:
        """Attach a media item as the featured image for a page."""
        result = self._post(
            f"{self.api_url}/pages/{page_id}",
            json={"featured_media": media_id},
        )
        log.info("wp_featured_image_set", page_id=page_id, media_id=media_id)
        return result

    # ------------------------------------------------------------------
    # Media
    # ------------------------------------------------------------------

    def upload_media(self, file_path: str, alt_text: str = "") -> dict:
        """Upload a local file to the WordPress media library.

        Returns the media object dict including `id` and `source_url`.
        """
        if not os.path.isfile(file_path):
            raise WordPressAPIError(f"File not found for media upload: {file_path}")

        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        filename = os.path.basename(file_path)
        with open(file_path, "rb") as fh:
            files = {
                "file": (filename, fh, mime_type),
            }
            headers_extra = {
                "Content-Disposition": f'attachment; filename="{filename}"',
            }
            # For media uploads we must bypass _request and use a raw call
            # because httpx handles multipart differently than json/data
            try:
                resp = self.client.post(
                    f"{self.api_url}/media",
                    files=files,
                    headers=headers_extra,
                )
            except httpx.RequestError as exc:
                raise WordPressAPIError(f"Network error uploading media: {exc}") from exc

        if resp.status_code == 401:
            raise WordPressAuthError("Invalid credentials")
        if resp.status_code == 404:
            raise WordPressNotFoundError("Media endpoint not found")
        if resp.status_code >= 500:
            raise WordPressServerError(f"WordPress server error {resp.status_code}: {resp.text[:200]}")
        if resp.status_code >= 400:
            raise WordPressAPIError(f"Media upload failed {resp.status_code}: {resp.text[:200]}")

        result = resp.json()

        # Optionally set alt text via a follow-up PATCH
        if alt_text and result.get("id"):
            try:
                self._post(
                    f"{self.api_url}/media/{result['id']}",
                    json={"alt_text": alt_text},
                )
            except WordPressAPIError:
                log.warning("wp_media_alt_text_failed", media_id=result.get("id"))

        log.info("wp_media_uploaded", media_id=result.get("id"), filename=filename)
        return result

    # ------------------------------------------------------------------
    # Menus
    # ------------------------------------------------------------------

    def create_menu(self, name: str, location: str) -> dict:
        """Create a navigation menu.

        WordPress REST API v2 does not expose menus natively in all setups.
        We use the /wp/v2/menus endpoint (available in WP 5.9+ with block themes,
        or via the WP REST API Menus plugin). Falls back gracefully if unavailable.
        """
        try:
            result = self._post(
                f"{self.base_url}/wp-json/wp/v2/menus",
                json={"name": name, "slug": name.lower().replace(" ", "-")},
            )
        except WordPressNotFoundError:
            # Fallback: try the older nav_menus taxonomy endpoint
            result = self._post(
                f"{self.base_url}/wp-json/wp/v2/nav_menu",
                json={"name": name, "slug": name.lower().replace(" ", "-")},
            )

        # Assign to theme location if supported
        menu_id = result.get("id")
        if menu_id and location:
            try:
                self._post(
                    f"{self.base_url}/wp-json/wp/v2/menus/{menu_id}",
                    json={"locations": [location]},
                )
            except WordPressAPIError:
                log.warning("wp_menu_location_assign_failed", menu_id=menu_id, location=location)

        log.info("wp_menu_created", menu_id=menu_id, name=name)
        return result

    def add_menu_item(self, menu_id: int, page_id: int, order: int) -> dict:
        """Add a page as a nav menu item."""
        from backend.platforms.wordpress.templates import menu_item_payload
        payload = menu_item_payload(page_id=page_id, order=order)
        payload["menus"] = menu_id

        try:
            result = self._post(
                f"{self.base_url}/wp-json/wp/v2/menu-items",
                json=payload,
            )
        except WordPressNotFoundError:
            # Older WP: attempt nav_menu_item post type
            result = self._post(
                f"{self.api_url}/nav_menu_item",
                json=payload,
            )

        log.info("wp_menu_item_added", menu_id=menu_id, page_id=page_id, order=order)
        return result

    # ------------------------------------------------------------------
    # Site settings
    # ------------------------------------------------------------------

    def update_site_settings(self, title: str, description: str) -> None:
        """Update the site title and tagline via the Settings API."""
        self._post(
            f"{self.base_url}/wp-json/wp/v2/settings",
            json={"title": title, "description": description},
        )
        log.info("wp_site_settings_updated", title=title)

    def set_front_page(self, page_id: int) -> None:
        """Set a specific page as the static front page."""
        self._post(
            f"{self.base_url}/wp-json/wp/v2/settings",
            json={"show_on_front": "page", "page_on_front": page_id},
        )
        log.info("wp_front_page_set", page_id=page_id)

    def set_blog_page(self, page_id: int) -> None:
        """Set a specific page as the posts/blog page."""
        self._post(
            f"{self.base_url}/wp-json/wp/v2/settings",
            json={"show_on_front": "page", "page_for_posts": page_id},
        )
        log.info("wp_blog_page_set", page_id=page_id)

    # ------------------------------------------------------------------
    # WooCommerce
    # ------------------------------------------------------------------

    def create_product(self, data: dict) -> dict:
        """Create a WooCommerce product. `data` is a full WC product payload."""
        result = self._post(f"{self.wc_url}/products", json=data)
        log.info("wc_product_created", product_id=result.get("id"), name=data.get("name"))
        return result

    def get_products(self) -> list[dict]:
        """Return all WooCommerce products (paginated)."""
        products: list[dict] = []
        page_num = 1
        while True:
            batch = self._get(
                f"{self.wc_url}/products",
                params={"per_page": 100, "page": page_num},
            )
            if not isinstance(batch, list) or not batch:
                break
            products.extend(batch)
            if len(batch) < 100:
                break
            page_num += 1
        return products

    # ------------------------------------------------------------------
    # SEO meta (Yoast / RankMath / custom fields)
    # ------------------------------------------------------------------

    def set_page_meta(
        self, page_id: int, meta_title: str, meta_description: str
    ) -> None:
        """Set Yoast SEO meta for a page.

        Attempts the Yoast v1 endpoint first, then falls back to storing as
        custom post meta via the standard pages endpoint.
        """
        # Yoast SEO exposes a dedicated endpoint on /wp-json/yoast/v1/indexables
        # but the simplest cross-plugin approach is to write _yoast_wpseo_title
        # and _yoast_wpseo_metadesc as post meta.
        meta_payload = {
            "meta": {
                "_yoast_wpseo_title": meta_title,
                "_yoast_wpseo_metadesc": meta_description,
                # RankMath support
                "rank_math_title": meta_title,
                "rank_math_description": meta_description,
            }
        }
        try:
            self._post(f"{self.api_url}/pages/{page_id}", json=meta_payload)
            log.info("wp_page_meta_set", page_id=page_id)
        except WordPressAPIError as exc:
            log.warning("wp_page_meta_failed", page_id=page_id, error=str(exc))
            raise

    def set_schema_markup(self, page_id: int, schema: dict) -> None:
        """Store JSON-LD schema markup as post meta on a page.

        Serialised as the _schema_markup custom field so it can be output
        by the active theme / SEO plugin.
        """
        import json

        meta_payload = {
            "meta": {
                "_schema_markup": json.dumps(schema, ensure_ascii=False),
            }
        }
        try:
            self._post(f"{self.api_url}/pages/{page_id}", json=meta_payload)
            log.info("wp_schema_set", page_id=page_id, schema_type=schema.get("@type"))
        except WordPressAPIError as exc:
            log.warning("wp_schema_failed", page_id=page_id, error=str(exc))
            raise

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying httpx client."""
        self.client.close()

    def __enter__(self) -> "WordPressClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
