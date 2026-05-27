"""
Content generation agent for the CloudIA agent system.

Generates professional page copy for each page in the pipeline plan and
writes results to the GeneratedContent table. Creates a content_review
approval gate when complete.
"""

from datetime import datetime, UTC
from typing import Any

import structlog
from sqlalchemy import select

from backend.agents.base import BaseAgent
from backend.ai.claude import call_claude_json
from backend.ai.context_builder import build_project_context
from backend.ai.prompts.content import (
    CONTENT_SYSTEM_PROMPT,
    CONTENT_PAGE_PROMPT_TEMPLATE,
    CONTENT_PRODUCT_PROMPT_TEMPLATE,
)
from backend.db.models import (
    AgentTask,
    ApprovalGate,
    Client,
    GeneratedContent,
    Project,
)
from backend.db.session import get_db

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Validation constants
# ---------------------------------------------------------------------------

MAX_META_TITLE_LEN = 60
MAX_META_DESC_LEN = 160
MIN_BODY_LEN = 100
MAX_RETRIES = 2
FORBIDDEN_STRINGS = ("lorem ipsum", "[placeholder]", "todo")


def _validate_content(content: dict) -> list[str]:
    """Return list of validation error strings. Empty list = valid."""
    errors: list[str] = []

    meta_title = content.get("meta_title", "")
    meta_desc = content.get("meta_description", "")
    body = content.get("body_content", "")

    if len(meta_title) > MAX_META_TITLE_LEN:
        errors.append(
            f"meta_title is {len(meta_title)} chars (max {MAX_META_TITLE_LEN}): "
            f"'{meta_title[:80]}'"
        )

    if len(meta_desc) > MAX_META_DESC_LEN:
        errors.append(
            f"meta_description is {len(meta_desc)} chars (max {MAX_META_DESC_LEN})"
        )

    if len(body) < MIN_BODY_LEN:
        errors.append(
            f"body_content is too short ({len(body)} chars, min {MIN_BODY_LEN})"
        )

    body_lower = body.lower()
    for forbidden in FORBIDDEN_STRINGS:
        if forbidden in body_lower:
            errors.append(f"body_content contains forbidden string: '{forbidden}'")

    title_lower = (content.get("title", "") + content.get("h1", "")).lower()
    for forbidden in FORBIDDEN_STRINGS:
        if forbidden in title_lower:
            errors.append(f"title/h1 contains forbidden string: '{forbidden}'")

    return errors


class ContentAgent(BaseAgent):
    """Generates page copy for every page in the pipeline plan."""

    agent_name = "content_agent"

    def run(self) -> dict:
        """
        1. Load project + client from DB
        2. Build context
        3. For each page: call Claude, validate, retry up to MAX_RETRIES times
        4. Write GeneratedContent records
        5. Write content_review ApprovalGate
        6. Update project.status
        7. Emit WebSocket event + email notification
        """
        # ------------------------------------------------------------------
        # Load project and client
        # ------------------------------------------------------------------
        with get_db() as db:
            project = db.get(Project, self.project_id)
            if project is None:
                raise RuntimeError(f"Project {self.project_id} not found")

            client = db.get(Client, project.client_id)
            if client is None:
                raise RuntimeError(f"Client {project.client_id} not found")

            platform: str = project.platform or "wordpress"
            pipeline_plan: dict = project.pipeline_plan or {}
            brief: dict = project.brief or {}

            db.expunge(project)
            db.expunge(client)

        self.log.info("content_agent_start", platform=platform)

        # ------------------------------------------------------------------
        # Build shared context
        # ------------------------------------------------------------------
        context = build_project_context(client, project)

        # ------------------------------------------------------------------
        # Determine page list
        # ------------------------------------------------------------------
        page_list: list[str] = pipeline_plan.get("page_list", [])
        content_requirements: dict = pipeline_plan.get("content_requirements", {})

        if not page_list:
            # Fall back to task input_data
            with get_db() as db:
                task = db.get(AgentTask, self.task_id)
                if task and task.input_data:
                    page_list = task.input_data.get("page_list", [])

        if not page_list:
            page_list = ["home", "about", "contact"]
            self.log.warning("content_agent_no_page_list_using_default")

        self.log.info("content_agent_pages", count=len(page_list))

        # ------------------------------------------------------------------
        # Generate content per page
        # ------------------------------------------------------------------
        total_tokens = 0
        total_cost = 0.0
        generated_count = 0
        failed_pages: list[str] = []
        gate_id: int | None = None

        for page_slug in page_list:
            page_purpose = content_requirements.get(
                page_slug,
                f"Standard {page_slug.replace('-', ' ').title()} page for this business",
            )

            prompt = (
                f"{context}\n\n"
                + CONTENT_PAGE_PROMPT_TEMPLATE.format(
                    page_slug=page_slug,
                    page_purpose=page_purpose,
                )
            )

            # Retry loop
            content: dict | None = None
            last_errors: list[str] = []

            for attempt in range(MAX_RETRIES + 1):
                try:
                    raw, tokens, cost = call_claude_json(
                        prompt=prompt,
                        system=CONTENT_SYSTEM_PROMPT,
                        max_tokens=3000,
                    )
                    total_tokens += tokens
                    total_cost += cost

                    errors = _validate_content(raw)
                    if errors:
                        last_errors = errors
                        self.log.warning(
                            "content_validation_failed",
                            page=page_slug,
                            attempt=attempt + 1,
                            errors=errors,
                        )
                        if attempt < MAX_RETRIES:
                            # Inject error feedback into next prompt
                            prompt = (
                                f"{context}\n\n"
                                + CONTENT_PAGE_PROMPT_TEMPLATE.format(
                                    page_slug=page_slug,
                                    page_purpose=page_purpose,
                                )
                                + f"\n\nPrevious attempt had these issues — fix them:\n"
                                + "\n".join(f"- {e}" for e in errors)
                            )
                            continue
                        else:
                            # Exhausted retries
                            break
                    else:
                        content = raw
                        break

                except Exception as exc:
                    self.log.error(
                        "content_claude_error",
                        page=page_slug,
                        attempt=attempt + 1,
                        error=str(exc),
                    )
                    last_errors = [str(exc)]
                    if attempt >= MAX_RETRIES:
                        break

            # Write to DB
            if content is not None:
                self._write_generated_content(
                    project_id=self.project_id,
                    page_slug=page_slug,
                    platform=platform,
                    content=content,
                )
                generated_count += 1
                self.log.info("content_page_written", page=page_slug)
            else:
                self.log.error(
                    "content_page_failed_after_retries",
                    page=page_slug,
                    errors=last_errors,
                )
                # Write a failed placeholder so the gate can track what broke
                self._write_generated_content(
                    project_id=self.project_id,
                    page_slug=page_slug,
                    platform=platform,
                    content={
                        "title": f"{page_slug.title()} (generation failed)",
                        "h1": "",
                        "body_content": "",
                        "cta_text": "",
                        "meta_title": "",
                        "meta_description": "",
                    },
                    status="failed",
                )
                failed_pages.append(page_slug)

        # ------------------------------------------------------------------
        # Generate Shopify product descriptions if applicable
        # ------------------------------------------------------------------
        product_count = 0
        if platform == "shopify" and brief.get("products"):
            products = brief["products"]
            if isinstance(products, list):
                for product in products:
                    p_name = product.get("name", "Product")
                    p_details = str(product)

                    prompt = (
                        f"{context}\n\n"
                        + CONTENT_PRODUCT_PROMPT_TEMPLATE.format(
                            product_name=p_name,
                            product_details=p_details[:500],
                        )
                    )

                    try:
                        raw, tokens, cost = call_claude_json(
                            prompt=prompt,
                            system=CONTENT_SYSTEM_PROMPT,
                            max_tokens=1024,
                        )
                        total_tokens += tokens
                        total_cost += cost

                        self._write_generated_content(
                            project_id=self.project_id,
                            page_slug=f"product-{p_name.lower().replace(' ', '-')}",
                            platform=platform,
                            content={
                                "title": raw.get("title", p_name),
                                "h1": raw.get("title", p_name),
                                "body_content": raw.get("description", ""),
                                "cta_text": "Add to Cart",
                                "meta_title": raw.get("meta_title", "")[:MAX_META_TITLE_LEN],
                                "meta_description": raw.get("meta_description", "")[:MAX_META_DESC_LEN],
                            },
                            content_type="product",
                        )
                        product_count += 1

                    except Exception as exc:
                        self.log.error(
                            "content_product_failed",
                            product=p_name,
                            error=str(exc),
                        )

        # ------------------------------------------------------------------
        # Create content_review ApprovalGate
        # ------------------------------------------------------------------
        gate_id = self._create_content_review_gate()

        # ------------------------------------------------------------------
        # Update project status
        # ------------------------------------------------------------------
        with get_db() as db:
            project = db.get(Project, self.project_id)
            if project:
                project.status = "awaiting_content_review"
                db.commit()

        # ------------------------------------------------------------------
        # Emit WebSocket event
        # ------------------------------------------------------------------
        try:
            from backend.api.websocket import send_project_event
            send_project_event(
                project_id=self.project_id,
                event_type="content_ready",
                data={
                    "pages_generated": generated_count,
                    "pages_failed": failed_pages,
                    "gate_id": gate_id,
                    "status": "awaiting_content_review",
                },
            )
        except Exception as ws_exc:
            self.log.warning("websocket_event_failed", error=str(ws_exc))

        # ------------------------------------------------------------------
        # Send email notification
        # ------------------------------------------------------------------
        try:
            from backend.notifications.email import notify_content_ready
            notify_content_ready(
                project_id=self.project_id,
                client_name=client.name or f"Client {client.id}",
                page_count=generated_count,
            )
        except Exception as email_exc:
            self.log.warning("email_notification_failed", error=str(email_exc))

        return {
            "pages_generated": generated_count,
            "pages_failed": failed_pages,
            "product_descriptions_generated": product_count,
            "gate_id": gate_id,
            "status": "awaiting_content_review",
            "_tokens_used": total_tokens,
            "_cost_usd": total_cost,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _write_generated_content(
        self,
        project_id: int,
        page_slug: str,
        platform: str,
        content: dict,
        content_type: str = "page",
        status: str = "draft",
    ) -> int:
        """Upsert a GeneratedContent record. Returns the record ID."""
        with get_db() as db:
            existing = db.execute(
                select(GeneratedContent).where(
                    GeneratedContent.project_id == project_id,
                    GeneratedContent.page_slug == page_slug,
                )
            ).scalar_one_or_none()

            if existing:
                existing.title = content.get("title", "")
                existing.h1 = content.get("h1", "")
                existing.body_content = content.get("body_content", "")
                existing.cta_text = content.get("cta_text", "")
                existing.meta_title = content.get("meta_title", "")
                existing.meta_description = content.get("meta_description", "")
                existing.status = status
                existing.content_type = content_type
                db.commit()
                return existing.id
            else:
                record = GeneratedContent(
                    project_id=project_id,
                    page_slug=page_slug,
                    content_type=content_type,
                    title=content.get("title", ""),
                    h1=content.get("h1", ""),
                    body_content=content.get("body_content", ""),
                    cta_text=content.get("cta_text", ""),
                    meta_title=content.get("meta_title", ""),
                    meta_description=content.get("meta_description", ""),
                    status=status,
                )
                db.add(record)
                db.commit()
                db.refresh(record)
                return record.id

    def _create_content_review_gate(self) -> int | None:
        """Create (or return existing) content_review ApprovalGate."""
        with get_db() as db:
            existing = db.execute(
                select(ApprovalGate).where(
                    ApprovalGate.project_id == self.project_id,
                    ApprovalGate.gate_name == "content_review",
                )
            ).scalar_one_or_none()

            if existing:
                existing.status = "pending"
                db.commit()
                return existing.id

            gate = ApprovalGate(
                project_id=self.project_id,
                gate_name="content_review",
                pipeline_order=1,
                status="pending",
            )
            db.add(gate)
            db.commit()
            db.refresh(gate)
            self.log.info("content_review_gate_created", gate_id=gate.id)
            return gate.id
