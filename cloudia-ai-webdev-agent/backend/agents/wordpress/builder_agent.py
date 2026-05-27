"""
WordPress Builder agent for the CloudIA agent system.

Constructs the WordPress site via the REST API using approved content,
media assets, and the structure plan.
"""

from datetime import datetime, UTC
from typing import Any

import structlog
from sqlalchemy import select

from backend.agents.base import BaseAgent
from backend.db.models import (
    ApprovalGate,
    Client,
    GeneratedContent,
    PlatformCredential,
    Project,
    ProjectMedia,
)
from backend.db.session import get_db

log = structlog.get_logger()


class WPBuilderAgent(BaseAgent):
    """Builds the WordPress site using the REST API."""

    agent_name = "wp_builder_agent"

    def run(self) -> dict:
        """
        1. Load credentials + project + content + media
        2. Initialize WordPress client
        3. Verify REST API accessible
        4. Upload media files
        5. Create pages with approved content
        6. Create navigation menus
        7. Configure site title + tagline
        8. Set homepage
        9. Create WooCommerce products if needed
        10. Set project.site_url + status + create site_review gate
        11. Emit WebSocket event
        """
        # ------------------------------------------------------------------
        # Load everything from DB
        # ------------------------------------------------------------------
        with get_db() as db:
            project = db.get(Project, self.project_id)
            if project is None:
                raise RuntimeError(f"Project {self.project_id} not found")

            client = db.get(Client, project.client_id)
            if client is None:
                raise RuntimeError(f"Client {project.client_id} not found")

            # Load approved content
            approved_content = db.execute(
                select(GeneratedContent).where(
                    GeneratedContent.project_id == self.project_id,
                    GeneratedContent.status == "approved",
                )
            ).scalars().all()

            # Load project media
            media_records = db.execute(
                select(ProjectMedia).where(
                    ProjectMedia.project_id == self.project_id,
                    ProjectMedia.is_placeholder.is_(False),
                )
            ).scalars().all()

            pipeline_plan: dict = project.pipeline_plan or {}
            brief: dict = project.brief or {}

            db.expunge(project)
            db.expunge(client)
            content_list = []
            for c in approved_content:
                db.expunge(c)
                content_list.append(c)
            media_list = []
            for m in media_records:
                db.expunge(m)
                media_list.append(m)

        if not content_list:
            raise RuntimeError(
                "No approved content found — cannot build WordPress site. "
                "Approve content in the content_review gate first."
            )

        self.log.info(
            "wp_builder_start",
            pages=len(content_list),
            media_count=len(media_list),
        )

        # ------------------------------------------------------------------
        # Initialize WordPress client
        # ------------------------------------------------------------------
        try:
            from backend.platforms.wordpress.client import WordPressClient
            wp = WordPressClient(project=project)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to initialise WordPress client: {exc}"
            ) from exc

        # ------------------------------------------------------------------
        # Verify REST API is accessible
        # ------------------------------------------------------------------
        if not wp.verify_connection():
            raise RuntimeError(
                "WordPress REST API is not accessible. "
                "Check site URL and credentials in project settings."
            )

        structure_plan: dict = pipeline_plan.get("structure_plan", {})
        pages_plan: list[dict] = structure_plan.get("pages", [])
        requires_woocommerce: bool = structure_plan.get(
            "requires_woocommerce",
            pipeline_plan.get("requires_woocommerce", False),
        )

        built_pages: dict[str, int] = {}   # slug → WP page ID
        partial_failures: list[dict] = []
        media_ids: dict[str, int] = {}     # page_slug → WP media ID

        # ------------------------------------------------------------------
        # Upload media
        # ------------------------------------------------------------------
        for media in media_list:
            try:
                wp_media_id = wp.upload_media(
                    local_path=media.optimised_path or media.local_path,
                    alt_text=media.alt_text or "",
                    attribution=media.attribution or "",
                )
                media_ids[media.page_slug] = wp_media_id

                # Write platform_id back to ProjectMedia
                with get_db() as db:
                    db_media = db.get(ProjectMedia, media.id)
                    if db_media:
                        db_media.platform_id = str(wp_media_id)
                        db.commit()

                self.log.info(
                    "wp_media_uploaded",
                    page=media.page_slug,
                    wp_media_id=wp_media_id,
                )
            except Exception as exc:
                self.log.error(
                    "wp_media_upload_failed",
                    page=media.page_slug,
                    error=str(exc),
                )
                # Non-fatal — continue without image for this page

        # ------------------------------------------------------------------
        # Create pages
        # ------------------------------------------------------------------
        for content in content_list:
            page_slug = content.page_slug

            # Find template from structure plan
            template = "page.php"
            for p in pages_plan:
                if p.get("slug") == page_slug:
                    template = p.get("template", "page.php")
                    break

            featured_media_id = media_ids.get(page_slug)

            try:
                wp_page_id = wp.create_or_update_page(
                    slug=page_slug,
                    title=content.title or page_slug.title(),
                    content=content.body_content or "",
                    meta_title=content.meta_title or "",
                    meta_description=content.meta_description or "",
                    template=template,
                    featured_media_id=featured_media_id,
                    status="publish",
                )
                built_pages[page_slug] = wp_page_id

                # Write platform_id back to GeneratedContent
                with get_db() as db:
                    db_content = db.get(GeneratedContent, content.id)
                    if db_content:
                        db_content.platform_id = str(wp_page_id)
                        db_content.status = "published"
                        db.commit()

                self.log.info(
                    "wp_page_created",
                    slug=page_slug,
                    wp_page_id=wp_page_id,
                )
            except Exception as exc:
                self.log.error(
                    "wp_page_failed",
                    slug=page_slug,
                    error=str(exc),
                )
                partial_failures.append({
                    "slug": page_slug,
                    "error": str(exc),
                })

        # ------------------------------------------------------------------
        # Create navigation menus
        # ------------------------------------------------------------------
        try:
            primary_menu = structure_plan.get("primary_menu", [])
            footer_menu = structure_plan.get("footer_menu", [])

            if primary_menu:
                wp.create_menu(
                    menu_name="Primary Menu",
                    menu_location="primary",
                    items=primary_menu,
                    built_pages=built_pages,
                )
                self.log.info("wp_primary_menu_created")

            if footer_menu:
                wp.create_menu(
                    menu_name="Footer Menu",
                    menu_location="footer",
                    items=footer_menu,
                    built_pages=built_pages,
                )
                self.log.info("wp_footer_menu_created")
        except Exception as exc:
            self.log.warning("wp_menus_failed", error=str(exc))
            partial_failures.append({"step": "menus", "error": str(exc)})

        # ------------------------------------------------------------------
        # Configure site title and tagline
        # ------------------------------------------------------------------
        try:
            site_title = client.name or "My Website"
            tagline = (client.usp or "")[:100]
            wp.update_site_settings(title=site_title, tagline=tagline)
            self.log.info("wp_site_settings_updated")
        except Exception as exc:
            self.log.warning("wp_site_settings_failed", error=str(exc))

        # ------------------------------------------------------------------
        # Set homepage as static page
        # ------------------------------------------------------------------
        homepage_slug = structure_plan.get("homepage_slug", "home")
        homepage_wp_id = built_pages.get(homepage_slug)
        if homepage_wp_id:
            try:
                wp.set_static_homepage(page_id=homepage_wp_id)
                self.log.info("wp_homepage_set", page_id=homepage_wp_id)
            except Exception as exc:
                self.log.warning("wp_homepage_set_failed", error=str(exc))
                partial_failures.append({"step": "set_homepage", "error": str(exc)})
        else:
            self.log.warning(
                "wp_homepage_page_not_found",
                homepage_slug=homepage_slug,
                built_pages=list(built_pages.keys()),
            )

        # ------------------------------------------------------------------
        # WooCommerce products (if required)
        # ------------------------------------------------------------------
        woo_products_created = 0
        if requires_woocommerce and brief.get("products"):
            woo_products_created = self._create_woocommerce_products(
                wp=wp,
                products=brief["products"],
                partial_failures=partial_failures,
            )

        # ------------------------------------------------------------------
        # Determine site URL
        # ------------------------------------------------------------------
        site_url = wp.get_site_url()

        # ------------------------------------------------------------------
        # Update project + create site_review gate
        # ------------------------------------------------------------------
        gate_id: int | None = None
        with get_db() as db:
            db_project = db.get(Project, self.project_id)
            if db_project:
                db_project.site_url = site_url
                db_project.status = "awaiting_site_review"
                db.commit()

            # Create site_review gate
            existing_gate = db.execute(
                select(ApprovalGate).where(
                    ApprovalGate.project_id == self.project_id,
                    ApprovalGate.gate_name == "site_review",
                )
            ).scalar_one_or_none()

            if not existing_gate:
                gate = ApprovalGate(
                    project_id=self.project_id,
                    gate_name="site_review",
                    pipeline_order=4,
                    status="pending",
                    notes=(
                        f"Site built with {len(built_pages)} pages. "
                        + (f"{len(partial_failures)} partial failures." if partial_failures else "")
                    ),
                )
                db.add(gate)
                db.commit()
                db.refresh(gate)
                gate_id = gate.id
            else:
                gate_id = existing_gate.id

        self.log.info(
            "wp_builder_complete",
            pages_built=len(built_pages),
            partial_failures=len(partial_failures),
            site_url=site_url,
        )

        # ------------------------------------------------------------------
        # Emit WebSocket event
        # ------------------------------------------------------------------
        try:
            from backend.api.websocket import send_project_event
            send_project_event(
                project_id=self.project_id,
                event_type="site_built",
                data={
                    "pages_built": len(built_pages),
                    "site_url": site_url,
                    "gate_id": gate_id,
                    "partial_failures": partial_failures,
                },
            )
        except Exception as ws_exc:
            self.log.warning("websocket_event_failed", error=str(ws_exc))

        return {
            "pages_built": len(built_pages),
            "built_pages": built_pages,
            "partial_failures": partial_failures,
            "woo_products_created": woo_products_created,
            "site_url": site_url,
            "gate_id": gate_id,
            "_tokens_used": 0,
            "_cost_usd": 0.0,
        }

    # ------------------------------------------------------------------
    # WooCommerce helpers
    # ------------------------------------------------------------------

    def _create_woocommerce_products(
        self,
        wp: Any,
        products: list[dict],
        partial_failures: list[dict],
    ) -> int:
        """Create products via WooCommerce REST API. Returns count created."""
        created = 0

        for product in products:
            p_name = product.get("name", "Product")
            p_price = product.get("price")

            # CRITICAL: never create a R0 or null price product
            if not p_price or str(p_price).strip() in ("0", "0.00", ""):
                self.log.error(
                    "woo_product_blocked_zero_price",
                    product_name=p_name,
                    price=p_price,
                )
                partial_failures.append({
                    "slug": f"woo-product-{p_name}",
                    "error": f"Product '{p_name}' blocked: price is R0 or null. "
                             f"Add a price to the brief before re-running.",
                })
                continue

            try:
                wp.create_woo_product(
                    name=p_name,
                    description=product.get("description", ""),
                    price=str(p_price),
                    sku=product.get("sku", ""),
                    stock=product.get("stock", 100),
                    categories=product.get("categories", []),
                )
                created += 1
                self.log.info("woo_product_created", name=p_name)
            except Exception as exc:
                self.log.error(
                    "woo_product_failed",
                    name=p_name,
                    error=str(exc),
                )
                partial_failures.append({
                    "slug": f"woo-product-{p_name}",
                    "error": str(exc),
                })

        return created
