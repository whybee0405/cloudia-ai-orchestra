"""
SEO agent for the CloudIA agent system.

Validates meta lengths, generates JSON-LD schema markup per page type,
produces an XML sitemap, and stores results on GeneratedContent records.
"""

import xml.etree.ElementTree as ET
from datetime import date, datetime, UTC
from typing import Any

import structlog
from sqlalchemy import select

from backend.agents.base import BaseAgent
from backend.ai.claude import call_claude_json
from backend.ai.context_builder import build_project_context
from backend.ai.prompts.seo import (
    SEO_SYSTEM_PROMPT,
    SEO_SCHEMA_PROMPT_TEMPLATE,
    SEO_VALIDATE_META_PROMPT_TEMPLATE,
)
from backend.db.models import Client, GeneratedContent, Project
from backend.db.session import get_db

log = structlog.get_logger()

MAX_META_TITLE = 60
MAX_META_DESC = 160


def _classify_page_type(slug: str) -> str:
    """Map a page slug to a schema type keyword."""
    slug_lower = slug.lower()
    if any(k in slug_lower for k in ("product", "shop", "store", "item")):
        return "product"
    if any(k in slug_lower for k in ("service", "services", "what-we-do")):
        return "service"
    if any(k in slug_lower for k in ("menu", "food", "restaurant", "dining")):
        return "restaurant"
    # Default: home, about, contact → LocalBusiness
    return "local_business"


def _build_sitemap_xml(site_url: str, slugs: list[str]) -> str:
    """Build a valid XML sitemap from site_url and page slugs."""
    urlset = ET.Element(
        "urlset",
        xmlns="http://www.sitemaps.org/schemas/sitemap/0.9",
    )

    today = date.today().isoformat()
    seen_urls: set[str] = set()

    for slug in slugs:
        # Normalise URL
        if slug in ("home", ""):
            loc = site_url.rstrip("/") + "/"
        else:
            loc = site_url.rstrip("/") + "/" + slug.strip("/") + "/"

        if loc in seen_urls:
            continue
        seen_urls.add(loc)

        url_el = ET.SubElement(urlset, "url")
        ET.SubElement(url_el, "loc").text = loc
        ET.SubElement(url_el, "lastmod").text = today
        ET.SubElement(url_el, "changefreq").text = "monthly"
        ET.SubElement(url_el, "priority").text = "1.0" if slug in ("home", "") else "0.8"

    tree = ET.ElementTree(urlset)
    ET.indent(tree, space="  ")

    xml_bytes = io.BytesIO()
    tree.write(xml_bytes, encoding="unicode", xml_declaration=True)
    return xml_bytes.getvalue()


# Need io for the in-memory buffer
import io


class SEOAgent(BaseAgent):
    """Validates meta, generates schema markup, produces XML sitemap."""

    agent_name = "seo_agent"

    def run(self) -> dict:
        """
        1. Load all published GeneratedContent for this project
        2. Validate meta lengths — flag (don't auto-truncate)
        3. Generate schema markup per page
        4. Generate + validate XML sitemap
        5. Store schema on GeneratedContent records
        6. Return seo_report
        """
        # ------------------------------------------------------------------
        # Load project + client + content
        # ------------------------------------------------------------------
        with get_db() as db:
            project = db.get(Project, self.project_id)
            if project is None:
                raise RuntimeError(f"Project {self.project_id} not found")

            client = db.get(Client, project.client_id)
            if client is None:
                raise RuntimeError(f"Client {project.client_id} not found")

            # SEO runs after content is published to the platform
            all_content = db.execute(
                select(GeneratedContent).where(
                    GeneratedContent.project_id == self.project_id,
                    GeneratedContent.status.in_(["approved", "published"]),
                )
            ).scalars().all()

            db.expunge(project)
            db.expunge(client)
            content_list = []
            for c in all_content:
                db.expunge(c)
                content_list.append(c)

        if not content_list:
            self.log.warning("seo_agent_no_content")
            return {
                "pages_processed": 0,
                "flags": ["No approved/published content found"],
                "_tokens_used": 0,
                "_cost_usd": 0.0,
            }

        platform: str = project.platform or "wordpress"
        site_url: str = project.site_url or ""

        self.log.info("seo_agent_start", pages=len(content_list), platform=platform)
        context = build_project_context(client, project)

        total_tokens = 0
        total_cost = 0.0
        page_reports: list[dict] = []
        all_flags: list[str] = []

        for content in content_list:
            page_slug = content.page_slug
            page_type = _classify_page_type(page_slug)

            page_report: dict[str, Any] = {
                "slug": page_slug,
                "meta_title_ok": True,
                "meta_title_length": len(content.meta_title or ""),
                "meta_description_ok": True,
                "meta_description_length": len(content.meta_description or ""),
                "has_schema": False,
                "schema_type": None,
                "issues": [],
            }

            # ----------------------------------------------------------
            # Validate meta lengths — flag only, never auto-truncate
            # ----------------------------------------------------------
            meta_title = content.meta_title or ""
            meta_desc = content.meta_description or ""

            if len(meta_title) > MAX_META_TITLE:
                flag = (
                    f"[{page_slug}] meta_title is {len(meta_title)} chars "
                    f"(max {MAX_META_TITLE}): '{meta_title[:80]}'"
                )
                all_flags.append(flag)
                page_report["meta_title_ok"] = False
                page_report["issues"].append(flag)

            if len(meta_desc) > MAX_META_DESC:
                flag = (
                    f"[{page_slug}] meta_description is {len(meta_desc)} chars "
                    f"(max {MAX_META_DESC})"
                )
                all_flags.append(flag)
                page_report["meta_description_ok"] = False
                page_report["issues"].append(flag)

            # ----------------------------------------------------------
            # Generate schema markup via Claude
            # ----------------------------------------------------------
            schema_prompt = (
                f"{context}\n\n"
                + SEO_SCHEMA_PROMPT_TEMPLATE.format(
                    page_slug=page_slug,
                    page_type=page_type,
                    page_title=content.title or page_slug,
                    meta_description=meta_desc[:160],
                )
            )

            try:
                schema_data, tokens, cost = call_claude_json(
                    prompt=schema_prompt,
                    system=SEO_SYSTEM_PROMPT,
                    max_tokens=1024,
                )
                total_tokens += tokens
                total_cost += cost

                schema_type = schema_data.get("@type", "LocalBusiness")
                page_report["has_schema"] = True
                page_report["schema_type"] = schema_type

                # Persist schema on the GeneratedContent record
                self._save_schema(content.id, schema_data)

                # Push schema to platform
                if site_url:
                    self._push_schema_to_platform(
                        platform=platform,
                        project=project,
                        page_slug=page_slug,
                        schema_data=schema_data,
                    )

            except Exception as exc:
                self.log.error(
                    "seo_schema_failed",
                    page=page_slug,
                    error=str(exc),
                )
                page_report["issues"].append(f"Schema generation failed: {exc}")

            page_reports.append(page_report)

        # ------------------------------------------------------------------
        # Generate XML sitemap
        # ------------------------------------------------------------------
        sitemap_xml: str = ""
        sitemap_url: str = ""
        sitemap_valid = False

        if site_url:
            slugs = [c.page_slug for c in content_list]
            try:
                sitemap_xml = _build_sitemap_xml(site_url, slugs)
                # Validate by parsing back
                ET.fromstring(sitemap_xml.encode() if isinstance(sitemap_xml, str) else sitemap_xml)
                sitemap_valid = True
                sitemap_url = site_url.rstrip("/") + "/sitemap.xml"
                self.log.info("seo_sitemap_generated", url_count=len(slugs))
            except ET.ParseError as exc:
                all_flags.append(f"Sitemap XML validation failed: {exc}")
                self.log.error("seo_sitemap_invalid", error=str(exc))

        # ------------------------------------------------------------------
        # Calculate overall score
        # ------------------------------------------------------------------
        total_issues = sum(len(p["issues"]) for p in page_reports)
        overall_score = max(0, 100 - (total_issues * 10))

        seo_report = {
            "pages": page_reports,
            "sitemap_url": sitemap_url,
            "sitemap_valid": sitemap_valid,
            "overall_score": overall_score,
            "flags": all_flags,
            "_tokens_used": total_tokens,
            "_cost_usd": total_cost,
        }

        self.log.info(
            "seo_agent_complete",
            pages=len(page_reports),
            score=overall_score,
            flags=len(all_flags),
        )

        return seo_report

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _save_schema(self, content_id: int, schema_data: dict) -> None:
        """Persist schema_markup on the GeneratedContent record."""
        with get_db() as db:
            record = db.get(GeneratedContent, content_id)
            if record:
                record.schema_markup = schema_data
                db.commit()

    def _push_schema_to_platform(
        self,
        platform: str,
        project: Project,
        page_slug: str,
        schema_data: dict,
    ) -> None:
        """Push schema markup to the platform via its client."""
        try:
            if platform == "wordpress":
                from backend.platforms.wordpress.client import WordPressClient
                wp = WordPressClient(project=project)
                wp.update_page_schema(page_slug=page_slug, schema=schema_data)
            elif platform == "shopify":
                from backend.platforms.shopify.client import ShopifyClient
                shopify = ShopifyClient(project=project)
                shopify.update_page_schema(page_slug=page_slug, schema=schema_data)
        except Exception as exc:
            # Schema push is best-effort — log warning, don't crash
            self.log.warning(
                "seo_schema_push_failed",
                platform=platform,
                page=page_slug,
                error=str(exc),
            )
