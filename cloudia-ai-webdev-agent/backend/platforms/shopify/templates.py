"""
Shopify Admin REST API payload builders for the CloudIA agent system.

These helpers produce the nested dict structures expected by the Shopify API,
isolating field-name knowledge from the higher-level client and agent code.
"""

from __future__ import annotations

from typing import Optional


def product_payload(
    title: str,
    description: str,
    price: str,
    vendor: str = "",
    variants: Optional[list] = None,
) -> dict:
    """Build a Shopify product creation/update payload.

    Args:
        title:       Product title.
        description: Body HTML for the product description.
        price:       Price string, e.g. ``"299.99"``.
        vendor:      Brand / vendor name. Defaults to empty (Shopify uses shop name).
        variants:    List of variant dicts. If omitted, a single default variant
                     is created with the given price. Each variant dict should
                     include at minimum ``{"price": "...", "option1": "Default Title"}``.

    Returns:
        dict: ``{"product": {...}}`` payload for POST/PUT to ``/products.json``.
    """
    if variants is None:
        variants = [
            {
                "price": str(price),
                "option1": "Default Title",
                "inventory_management": None,
                "fulfillment_service": "manual",
            }
        ]

    payload: dict = {
        "product": {
            "title": title,
            "body_html": description,
            "status": "draft",
            "variants": variants,
        }
    }
    if vendor:
        payload["product"]["vendor"] = vendor

    return payload


def collection_payload(title: str, description: str) -> dict:
    """Build a Shopify custom collection creation payload.

    Args:
        title:       Collection title displayed in the storefront.
        description: HTML body/description for the collection.

    Returns:
        dict: ``{"custom_collection": {...}}`` payload.
    """
    return {
        "custom_collection": {
            "title": title,
            "body_html": description,
            "published": False,
        }
    }


def page_payload(title: str, body_html: str, handle: str) -> dict:
    """Build a Shopify online store page payload.

    Args:
        title:     Page title.
        body_html: Page body HTML content.
        handle:    URL handle / slug, e.g. ``"about-us"``.

    Returns:
        dict: ``{"page": {...}}`` payload for POST to ``/pages.json``.
    """
    return {
        "page": {
            "title": title,
            "body_html": body_html,
            "handle": handle,
            "published": False,
        }
    }


def menu_payload(title: str, handle: str, items: list) -> dict:
    """Build a Shopify navigation menu payload.

    Args:
        title:  Menu title, e.g. ``"Main Navigation"``.
        handle: Menu handle / slug, e.g. ``"main-menu"``.
        items:  List of menu item dicts. Each item should include at minimum:
                ``{"title": "...", "url": "...", "type": "..."}``
                where ``type`` is one of ``"http"``, ``"collection"``,
                ``"product"``, ``"page"``, ``"blog"``, ``"frontpage"``.

    Returns:
        dict: ``{"menu": {...}}`` payload for POST/PUT to ``/menus.json``.
    """
    return {
        "menu": {
            "title": title,
            "handle": handle,
            "items": items,
        }
    }
