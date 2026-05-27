"""
Shopify Builder agent for the CloudIA agent system.

Constructs the Shopify store via the Admin REST API using approved content,
media assets, structure plan, and client brief.
"""

from typing import Any

import structlog
from sqlalchemy import select

from backend.agents.base import BaseAgent
from backend.db.models import (
    ApprovalGate,
    Client,
    GeneratedContent,
    Project,
    ProjectMedia,
)
from backend.db.session import get_db

log = structlog.get_logger()


class ShopifyBuilderAgent(BaseAgent):
    """Builds the Shopify store using the Admin REST API."""

    agent_name = "shopify_builder_agent"

    def run(self) -> dict:
        """
        1. Load credentials + project + content + media
        2. Initialize Shopify client
        3. Create collections
        4. Create products (CRITICAL: block R0 / null price)
        5. Assign products to collections
        6. Upload product images
        7. Create static pages
        8. Create navigation menus
        9. Set store metadata
        10. Update project + create store_review gate
        11. Emit WebSocket event
        """
        # ------------------------------------------------------------------
        # Load data
        # ------------------------------------------------------------------
        with get_db() as db:
            project = db.get(Project, self.project_id)
            if project is None:
                raise RuntimeError(f"Project {self.project_id} not found")

            client = db.get(Client, project.client_id)
            if client is None:
                raise RuntimeError(f"Client {project.client_id} not found")

            approved_content = db.execute(
                select(GeneratedContent).where(
                    GeneratedContent.project_id == self.project_id,
                    GeneratedContent.status == "approved",
                )
            ).scalars().all()

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
                "No approved content found — cannot build Shopify store. "
                "Approve content in the content_review gate first."
            )

        self.log.info(
            "shopify_builder_start",
            content_count=len(content_list),
            media_count=len(media_list),
        )

        # ------------------------------------------------------------------
        # Initialize Shopify client
        # ------------------------------------------------------------------
        try:
            from backend.platforms.shopify.client import ShopifyClient
            shopify = ShopifyClient(project=project)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to initialise Shopify client: {exc}"
            ) from exc

        structure_plan: dict = pipeline_plan.get("structure_plan", {})
        partial_failures: list[dict] = []
        blocked_products: list[str] = []

        # ------------------------------------------------------------------
        # Create collections
        # ------------------------------------------------------------------
        collections = structure_plan.get("collections", [])
        collection_ids: dict[str, int] = {}  # slug → Shopify collection ID

        for coll in collections:
            coll_name = coll.get("name", "Collection")
            coll_slug = coll.get("slug", coll_name.lower().replace(" ", "-"))
            try:
                coll_id = shopify.create_collection(
                    title=coll_name,
                    description=coll.get("description", ""),
                    handle=coll_slug,
                    sort_order=coll.get("sort_order", "best-selling"),
                )
                collection_ids[coll_slug] = coll_id
                self.log.info("shopify_collection_created", name=coll_name, id=coll_id)
            except Exception as exc:
                self.log.error(
                    "shopify_collection_failed",
                    name=coll_name,
                    error=str(exc),
                )
                partial_failures.append({"step": f"collection:{coll_name}", "error": str(exc)})

        # ------------------------------------------------------------------
        # Create products
        # ------------------------------------------------------------------
        products_from_brief: list[dict] = brief.get("products", [])
        if not isinstance(products_from_brief, list):
            products_from_brief = []

        product_content = [c for c in content_list if c.content_type == "product"]
        product_ids: dict[str, int] = {}  # slug → Shopify product ID

        for product_data in products_from_brief:
            if not isinstance(product_data, dict):
                continue

            p_name = product_data.get("name", "Product")
            p_slug = "product-" + p_name.lower().replace(" ", "-")
            p_price = product_data.get("price")

            # CRITICAL: Block R0 / null price
            if not p_price or str(p_price).strip() in ("0", "0.00", ""):
                msg = (
                    f"Product '{p_name}' blocked: price is R0 or null. "
                    "This product would be purchasable for free. "
                    "Add a price to the brief before re-running."
                )
                self.log.error("shopify_product_blocked_zero_price", product=p_name)
                blocked_products.append(p_name)
                partial_failures.append({"step": f"product:{p_name}", "error": msg})
                continue

            # Get matching content description
            p_description = product_data.get("description", "")
            for pc in product_content:
                if p_slug in pc.page_slug or p_name.lower() in (pc.title or "").lower():
                    p_description = pc.body_content or p_description
                    break

            # Get media for this product
            product_image_path: str | None = None
            for media in media_list:
                if p_slug in media.page_slug or p_name.lower() in (media.page_slug or ""):
                    product_image_path = media.optimised_path or media.local_path
                    break

            try:
                product_id = shopify.create_product(
                    title=p_name,
                    body_html=p_description,
                    vendor=client.name or "CloudIA",
                    price=str(p_price),
                    compare_at_price=str(product_data.get("compare_at_price", ""))
                    if product_data.get("compare_at_price")
                    else None,
                    sku=product_data.get("sku", ""),
                    inventory_quantity=product_data.get("stock", 100),
                    image_path=product_image_path,
                    alt_text=f"{p_name} — {client.name}",
                )
                product_ids[p_slug] = product_id
                self.log.info("shopify_product_created", name=p_name, id=product_id)

                # Update GeneratedContent with platform_id
                with get_db() as db:
                    for pc in product_content:
                        if p_slug in pc.page_slug:
                            db_content = db.get(GeneratedContent, pc.id)
                            if db_content:
                                db_content.platform_id = str(product_id)
                                db_content.status = "published"
                                db.commit()
                            break

            except Exception as exc:
                self.log.error(
                    "shopify_product_failed",
                    name=p_name,
                    error=str(exc),
                )
                partial_failures.append({"step": f"product:{p_name}", "error": str(exc)})

        # ------------------------------------------------------------------
        # Assign products to collections
        # ------------------------------------------------------------------
        products_per_collection: dict = structure_plan.get("products_per_collection", {})
        for coll_slug, product_slugs in products_per_collection.items():
            coll_id = collection_ids.get(coll_slug)
            if not coll_id:
                continue
            for p_slug in product_slugs:
                prod_id = product_ids.get(p_slug)
                if not prod_id:
                    continue
                try:
                    shopify.assign_product_to_collection(
                        product_id=prod_id,
                        collection_id=coll_id,
                    )
                except Exception as exc:
                    self.log.warning(
                        "shopify_collect_failed",
                        product=p_slug,
                        collection=coll_slug,
                        error=str(exc),
                    )

        # ------------------------------------------------------------------
        # Create static pages
        # ------------------------------------------------------------------
        pages_in_structure = structure_plan.get("pages", [])
        page_content = [c for c in content_list if c.content_type != "product"]
        built_pages: dict[str, int] = {}

        for content in page_content:
            page_slug = content.page_slug
            try:
                page_id = shopify.create_page(
                    title=content.title or page_slug.title(),
                    body_html=content.body_content or "",
                    handle=page_slug,
                )
                built_pages[page_slug] = page_id

                # Update platform_id
                with get_db() as db:
                    db_content = db.get(GeneratedContent, content.id)
                    if db_content:
                        db_content.platform_id = str(page_id)
                        db_content.status = "published"
                        db.commit()

                self.log.info("shopify_page_created", slug=page_slug, id=page_id)
            except Exception as exc:
                self.log.error(
                    "shopify_page_failed",
                    slug=page_slug,
                    error=str(exc),
                )
                partial_failures.append({"step": f"page:{page_slug}", "error": str(exc)})

        # ------------------------------------------------------------------
        # Create navigation menus
        # ------------------------------------------------------------------
        try:
            primary_menu = structure_plan.get("primary_menu", [])
            footer_menu = structure_plan.get("footer_menu", [])

            if primary_menu:
                shopify.create_menu(
                    title="Main Menu",
                    handle="main-menu",
                    items=primary_menu,
                )
                self.log.info("shopify_primary_menu_created")

            if footer_menu:
                shopify.create_menu(
                    title="Footer Menu",
                    handle="footer",
                    items=footer_menu,
                )
                self.log.info("shopify_footer_menu_created")
        except Exception as exc:
            self.log.warning("shopify_menus_failed", error=str(exc))
            partial_failures.append({"step": "menus", "error": str(exc)})

        # ------------------------------------------------------------------
        # Set store metadata
        # ------------------------------------------------------------------
        try:
            shopify.update_store_metadata(
                store_name=client.name or "My Store",
                store_email=client.contact_email or "",
            )
        except Exception as exc:
            self.log.warning("shopify_metadata_failed", error=str(exc))

        # ------------------------------------------------------------------
        # Determine store URL
        # ------------------------------------------------------------------
        store_url = shopify.get_store_url()

        # ------------------------------------------------------------------
        # Update project + create store_review gate
        # ------------------------------------------------------------------
        gate_id: int | None = None
        with get_db() as db:
            db_project = db.get(Project, self.project_id)
            if db_project:
                db_project.site_url = store_url
                db_project.status = "awaiting_store_review"
                db.commit()

            existing_gate = db.execute(
                select(ApprovalGate).where(
                    ApprovalGate.project_id == self.project_id,
                    ApprovalGate.gate_name == "store_review",
                )
            ).scalar_one_or_none()

            if not existing_gate:
                notes = None
                if blocked_products:
                    notes = f"Blocked products (R0 price): {', '.join(blocked_products)}"
                if partial_failures:
                    failures_summary = f"{len(partial_failures)} partial failures."
                    notes = (notes + " " + failures_summary) if notes else failures_summary

                gate = ApprovalGate(
                    project_id=self.project_id,
                    gate_name="store_review",
                    pipeline_order=4,
                    status="pending",
                    notes=notes,
                )
                db.add(gate)
                db.commit()
                db.refresh(gate)
                gate_id = gate.id
            else:
                gate_id = existing_gate.id

        self.log.info(
            "shopify_builder_complete",
            products=len(product_ids),
            collections=len(collection_ids),
            pages=len(built_pages),
            blocked=len(blocked_products),
            failures=len(partial_failures),
            store_url=store_url,
        )

        # ------------------------------------------------------------------
        # Emit WebSocket event
        # ------------------------------------------------------------------
        try:
            from backend.api.websocket import send_project_event
            send_project_event(
                project_id=self.project_id,
                event_type="store_built",
                data={
                    "products_created": len(product_ids),
                    "collections_created": len(collection_ids),
                    "pages_created": len(built_pages),
                    "blocked_products": blocked_products,
                    "store_url": store_url,
                    "gate_id": gate_id,
                },
            )
        except Exception as ws_exc:
            self.log.warning("websocket_event_failed", error=str(ws_exc))

        return {
            "products_created": len(product_ids),
            "collections_created": len(collection_ids),
            "pages_created": len(built_pages),
            "blocked_products": blocked_products,
            "partial_failures": partial_failures,
            "store_url": store_url,
            "gate_id": gate_id,
            "_tokens_used": 0,
            "_cost_usd": 0.0,
        }
