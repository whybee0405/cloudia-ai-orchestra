"""
Shopify Structure agent for the CloudIA agent system.

Plans the Shopify store architecture: collections, navigation menus,
static pages, and product organisation.
"""

import structlog
from sqlalchemy import select

from backend.agents.base import BaseAgent
from backend.ai.claude import call_claude_json
from backend.ai.context_builder import build_project_context
from backend.ai.prompts.shopify_structure import (
    SHOPIFY_STRUCTURE_SYSTEM_PROMPT,
    SHOPIFY_STRUCTURE_PROMPT_TEMPLATE,
)
from backend.db.models import Client, GeneratedContent, Project
from backend.db.session import get_db

log = structlog.get_logger()


class ShopifyStructureAgent(BaseAgent):
    """Plans the Shopify store architecture using approved content."""

    agent_name = "shopify_structure_agent"

    def run(self) -> dict:
        """
        1. Load project + client + approved content
        2. Build context
        3. Call Claude to generate store structure plan
        4. Merge structure_plan into project.pipeline_plan
        5. Return structure_plan
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

            pipeline_plan: dict = project.pipeline_plan or {}
            brief: dict = project.brief or {}

            db.expunge(project)
            db.expunge(client)
            content_list = []
            for c in approved_content:
                db.expunge(c)
                content_list.append(c)

        self.log.info(
            "shopify_structure_start",
            page_count=len(content_list),
        )

        context = build_project_context(client, project)

        # Derive page list and product list
        page_list = [c.page_slug for c in content_list if c.content_type != "product"]
        product_list = [c.page_slug for c in content_list if c.content_type == "product"]

        # Also check brief for products
        brief_products = brief.get("products", [])
        if isinstance(brief_products, list) and brief_products:
            for p in brief_products:
                p_slug = (
                    "product-" + p.get("name", "product").lower().replace(" ", "-")
                    if isinstance(p, dict)
                    else str(p)
                )
                if p_slug not in product_list:
                    product_list.append(p_slug)

        requires_blog = pipeline_plan.get("requires_blog", False)

        # ------------------------------------------------------------------
        # Build prompt
        # ------------------------------------------------------------------
        prompt = (
            f"{context}\n\n"
            + SHOPIFY_STRUCTURE_PROMPT_TEMPLATE.format(
                page_list=", ".join(page_list) if page_list else "about, contact",
                products_list=", ".join(product_list) if product_list else "none specified",
                requires_blog=str(requires_blog).lower(),
            )
        )

        # ------------------------------------------------------------------
        # Call Claude
        # ------------------------------------------------------------------
        structure_plan, tokens, cost = call_claude_json(
            prompt=prompt,
            system=SHOPIFY_STRUCTURE_SYSTEM_PROMPT,
            max_tokens=3000,
        )

        self.log.info(
            "shopify_structure_claude_complete",
            collections=len(structure_plan.get("collections", [])),
            pages=len(structure_plan.get("pages", [])),
        )

        # ------------------------------------------------------------------
        # Validate
        # ------------------------------------------------------------------
        self._validate_structure(structure_plan)

        # ------------------------------------------------------------------
        # Merge into project.pipeline_plan
        # ------------------------------------------------------------------
        with get_db() as db:
            db_project = db.get(Project, self.project_id)
            if db_project:
                current_plan = db_project.pipeline_plan or {}
                current_plan["structure_plan"] = structure_plan
                db_project.pipeline_plan = current_plan
                db.commit()

        self.log.info("shopify_structure_plan_saved")

        return {
            "structure_plan": structure_plan,
            "collections_planned": len(structure_plan.get("collections", [])),
            "pages_planned": len(structure_plan.get("pages", [])),
            "requires_blog": structure_plan.get("requires_blog", False),
            "_tokens_used": tokens,
            "_cost_usd": cost,
        }

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_structure(self, plan: dict) -> None:
        """Log warnings for structural issues."""
        collections = plan.get("collections", [])
        primary_menu = plan.get("primary_menu", [])

        if not primary_menu:
            self.log.warning("shopify_structure_no_primary_menu")

        if len(primary_menu) > 7:
            self.log.warning(
                "shopify_structure_primary_menu_too_large",
                count=len(primary_menu),
            )

        for coll in collections:
            if not coll.get("slug"):
                self.log.warning(
                    "shopify_structure_collection_missing_slug",
                    name=coll.get("name"),
                )

        currency = plan.get("default_currency", "ZAR")
        if currency != "ZAR":
            self.log.warning(
                "shopify_structure_non_zar_currency",
                currency=currency,
            )
