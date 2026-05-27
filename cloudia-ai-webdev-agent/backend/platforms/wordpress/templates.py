"""
WordPress REST API payload builders for the CloudIA agent system.

These helpers construct the dict payloads expected by the WP REST API,
keeping field-name knowledge in one place and out of the higher-level client
and agent code.
"""

from __future__ import annotations


def page_payload(
    title: str,
    content: str,
    slug: str,
    status: str = "draft",
    template: str = "",
    parent_id: int = 0,
) -> dict:
    """Build a WP REST API page creation/update payload.

    Args:
        title:     Page title (plain text — WP stores it as rendered HTML).
        content:   Page body HTML.
        slug:      URL slug, e.g. ``"about-us"``.
        status:    Publication status: ``"draft"`` | ``"publish"`` | ``"private"``.
        template:  Theme template filename, e.g. ``"page-full-width.php"``.
                   Empty string keeps the default template.
        parent_id: ID of the parent page for hierarchical pages (0 = top-level).

    Returns:
        dict: Ready to pass as the ``json=`` kwarg to :class:`WordPressClient`.
    """
    payload: dict = {
        "title": title,
        "content": content,
        "slug": slug,
        "status": status,
    }
    if template:
        payload["template"] = template
    if parent_id:
        payload["parent"] = parent_id
    return payload


def media_payload(alt_text: str) -> dict:
    """Build the metadata patch payload for a media item.

    Used after uploading a file to set its ``alt_text`` field.

    Args:
        alt_text: Accessibility alt text and SEO description for the image.

    Returns:
        dict: Partial media object payload suitable for a POST to ``/wp/v2/media/{id}``.
    """
    return {
        "alt_text": alt_text,
    }


def product_payload(
    name: str,
    description: str,
    price: str,
    images: list,
) -> dict:
    """Build a WooCommerce product creation payload.

    Args:
        name:        Product name.
        description: Full HTML product description.
        price:       Regular price as a string, e.g. ``"299.99"``.
        images:      List of image dicts, each with at least ``"src"`` and optionally
                     ``"alt"`` and ``"name"`` keys. Example::

                         [{"src": "https://example.com/img.jpg", "alt": "Red widget"}]

    Returns:
        dict: WooCommerce product payload for ``POST /wc/v3/products``.
    """
    payload: dict = {
        "name": name,
        "type": "simple",
        "status": "draft",
        "description": description,
        "regular_price": str(price),
        "catalog_visibility": "visible",
    }
    if images:
        payload["images"] = images
    return payload


def menu_item_payload(page_id: int, order: int) -> dict:
    """Build a WP nav-menu item payload.

    Creates a link to an existing page (``object_type=post_type``,
    ``object=page``).

    Args:
        page_id: ID of the target WordPress page.
        order:   Position in the menu (1-based).

    Returns:
        dict: Payload for ``POST /wp/v2/menu-items``.
    """
    return {
        "type": "post_type",
        "object": "page",
        "object_id": page_id,
        "menu_order": order,
        "status": "publish",
    }
