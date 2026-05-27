"""
WordPress Structure agent for the CloudIA agent system.

Plans the full WordPress site architecture: page hierarchy, navigation menus,
template assignments, and plugin requirements.
"""

import structlog
from sqlalchemy import select

from backend.agents.base import BaseAgent
from backend.ai.claude import call_claude_json
from backend.ai.context_builder import build_project_context
from backend.ai.prompts.wp_structure import (
    WP_STRUCTURE_SYSTEM_PROMPT,
    WP_STRUCTURE_PROMPT_TEMPLATE,
)
from backend.db.models import Client, GeneratedContent, Project
from backend.db.session import get_db

log = structlog.get_logger()


class WPStructureAgent(BaseAgent):
    """Plans the WordPress site architecture using approved content."""

    agent_name = "wp_structure_agent"

    def run(self) -> dict:
        """
        1. Load project + client + approved content
        2. Build context
        3. Call Claude to generate site structure plan
        4. Merge structure_plan into project.pipeline_plan
        5. Return structure_plan
        """
        # ------------------------------------------------------------------
        # Load project, client, and content
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
            db.expunge(project)
            db.expunge(client)
            content_list = []
            for c in approved_content:
                db.expunge(c)
                content_list.append(c)

        self.log.info("wp_structure_start", page_count=len(content_list))

        context = build_project_context(client, project)

        # Derive details from pipeline plan
        page_list = [c.page_slug for c in content_list]
        if not page_list:
            page_list = pipeline_plan.get("page_list", ["home", "about", "contact"])

        requires_woocommerce = pipeline_plan.get("requires_woocommerce", False)
        requires_blog = pipeline_plan.get("requires_blog", False)

        # ------------------------------------------------------------------
        # Build prompt
        # ------------------------------------------------------------------
        prompt = (
            f"{context}\n\n"
            + WP_STRUCTURE_PROMPT_TEMPLATE.format(
                page_list=", ".join(page_list),
                requires_woocommerce=str(requires_woocommerce).lower(),
                requires_blog=str(requires_blog).lower(),
            )
        )

        # ------------------------------------------------------------------
        # Call Claude
        # ------------------------------------------------------------------
        structure_plan, tokens, cost = call_claude_json(
            prompt=prompt,
            system=WP_STRUCTURE_SYSTEM_PROMPT,
            max_tokens=3000,
        )

        self.log.info(
            "wp_structure_claude_complete",
            page_count=len(structure_plan.get("pages", [])),
            requires_woocommerce=structure_plan.get("requires_woocommerce"),
        )

        # ------------------------------------------------------------------
        # Validate structure plan
        # ------------------------------------------------------------------
        self._validate_structure(structure_plan, page_list)

        # ------------------------------------------------------------------
        # Merge structure_plan into project.pipeline_plan
        # ------------------------------------------------------------------
        with get_db() as db:
            db_project = db.get(Project, self.project_id)
            if db_project:
                current_plan = db_project.pipeline_plan or {}
                current_plan["structure_plan"] = structure_plan
                db_project.pipeline_plan = current_plan
                db.commit()

        self.log.info("wp_structure_plan_saved")

        return {
            "structure_plan": structure_plan,
            "pages_planned": len(structure_plan.get("pages", [])),
            "requires_woocommerce": structure_plan.get("requires_woocommerce", False),
            "requires_blog": structure_plan.get("requires_blog", False),
            "_tokens_used": tokens,
            "_cost_usd": cost,
        }

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_structure(self, plan: dict, expected_slugs: list[str]) -> None:
        """Log warnings for structural issues without raising."""
        plan_slugs = {p.get("slug", "") for p in plan.get("pages", [])}
        homepage_slug = plan.get("homepage_slug", "home")

        if homepage_slug not in plan_slugs:
            self.log.warning(
                "wp_structure_homepage_missing",
                homepage_slug=homepage_slug,
                available_slugs=list(plan_slugs),
            )

        primary_menu = plan.get("primary_menu", [])
        if len(primary_menu) == 0:
            self.log.warning("wp_structure_no_primary_menu")
        elif len(primary_menu) > 7:
            self.log.warning(
                "wp_structure_primary_menu_too_large",
                count=len(primary_menu),
            )

        # Warn about pages in expected_slugs but missing from plan
        for slug in expected_slugs:
            if slug not in plan_slugs:
                self.log.warning("wp_structure_page_missing_from_plan", slug=slug)
