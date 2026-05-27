"""
Mock WordPress REST API client for the CloudIA test suite.

Provides:
  - MockWordPressClient — records calls, supports configurable failures
  - mock_wp_client context manager — patches WordPressClient constructor
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch

from backend.platforms.wordpress.client import (
    WordPressAPIError,
    WordPressAuthError,
    WordPressMaintenanceError,
    WordPressServerError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_wp_response(
    page_id: int = 1,
    title: str = "Test Page",
    status: str = "draft",
) -> dict:
    """Return a minimal WP REST API page response dict."""
    return {
        "id": page_id,
        "title": {"rendered": title},
        "status": status,
        "link": f"https://test.co.za/?p={page_id}",
        "slug": title.lower().replace(" ", "-"),
    }


# ---------------------------------------------------------------------------
# MockWordPressClient
# ---------------------------------------------------------------------------


class MockWordPressClient:
    """Configurable mock for WordPressClient.

    Args:
        fail_on_page: 1-indexed page number to raise WordPressServerError on.
        auth_fail:    Raise WordPressAuthError on every call.
        server_error: Raise WordPressServerError on every create_page call.
        maintenance:  Raise WordPressMaintenanceError on verify_connection.
    """

    def __init__(
        self,
        fail_on_page: int | None = None,
        auth_fail: bool = False,
        server_error: bool = False,
        maintenance: bool = False,
    ) -> None:
        self.fail_on_page = fail_on_page
        self.auth_fail = auth_fail
        self.server_error = server_error
        self.maintenance = maintenance
        self.calls: list[tuple] = []
        self._page_counter = 0

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def verify_connection(self) -> bool:
        self.calls.append(("verify_connection",))
        if self.auth_fail:
            raise WordPressAuthError("Invalid credentials — 401 Unauthorized")
        if self.maintenance:
            raise WordPressMaintenanceError("Site is in maintenance mode")
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
        self._page_counter += 1
        self.calls.append(("create_page", title, slug))
        if self.auth_fail:
            raise WordPressAuthError("401 Unauthorized")
        if self.server_error:
            raise WordPressServerError("500 Internal Server Error")
        if self.fail_on_page and self._page_counter == self.fail_on_page:
            raise WordPressServerError(
                f"Simulated failure on page #{self._page_counter}"
            )
        return make_wp_response(page_id=self._page_counter, title=title, status=status)

    def update_page(self, page_id: int, data: dict) -> dict:
        self.calls.append(("update_page", page_id))
        return make_wp_response(page_id=page_id)

    def get_page(self, page_id: int) -> dict:
        self.calls.append(("get_page", page_id))
        return make_wp_response(page_id=page_id)

    def get_all_pages(self) -> list[dict]:
        self.calls.append(("get_all_pages",))
        return [make_wp_response(i, f"Page {i}") for i in range(1, self._page_counter + 1)]

    def set_featured_image(self, page_id: int, media_id: int) -> dict:
        self.calls.append(("set_featured_image", page_id, media_id))
        return {}

    # ------------------------------------------------------------------
    # Media
    # ------------------------------------------------------------------

    def upload_media(self, file_path: str, alt_text: str = "") -> dict:
        self.calls.append(("upload_media", file_path))
        return {
            "id": 99,
            "source_url": "https://test.co.za/wp-content/uploads/test.jpg",
            "alt_text": alt_text,
        }

    # ------------------------------------------------------------------
    # Menus
    # ------------------------------------------------------------------

    def create_menu(self, name: str, location: str) -> dict:
        self.calls.append(("create_menu", name, location))
        return {"id": 1, "name": name}

    def add_menu_item(self, menu_id: int, page_id: int, order: int) -> dict:
        self.calls.append(("add_menu_item", menu_id, page_id, order))
        return {"id": order}

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def update_site_settings(self, title: str, description: str) -> None:
        self.calls.append(("update_site_settings", title, description))

    def set_front_page(self, page_id: int) -> None:
        self.calls.append(("set_front_page", page_id))

    def set_blog_page(self, page_id: int) -> None:
        self.calls.append(("set_blog_page", page_id))

    # ------------------------------------------------------------------
    # SEO
    # ------------------------------------------------------------------

    def set_page_meta(
        self, page_id: int, meta_title: str, meta_description: str
    ) -> None:
        self.calls.append(("set_page_meta", page_id, meta_title, meta_description))

    def set_schema_markup(self, page_id: int, schema: dict) -> None:
        self.calls.append(("set_schema_markup", page_id))

    # ------------------------------------------------------------------
    # WooCommerce
    # ------------------------------------------------------------------

    def create_product(self, data: dict) -> dict:
        self.calls.append(("create_product", data.get("name")))
        return {"id": 1, "name": data.get("name"), "status": "publish"}

    def get_products(self) -> list[dict]:
        return []

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
def mock_wp_client(**kwargs):
    """Patch WordPressClient to return a MockWordPressClient.

    Usage::

        with mock_wp_client(auth_fail=True) as mock:
            # code under test
            ...
        assert any(c[0] == "verify_connection" for c in mock.calls)
    """
    mock = MockWordPressClient(**kwargs)
    # Patch wherever WordPressClient is imported and used in the codebase
    with patch(
        "backend.platforms.wordpress.client.WordPressClient",
        return_value=mock,
    ):
        yield mock
