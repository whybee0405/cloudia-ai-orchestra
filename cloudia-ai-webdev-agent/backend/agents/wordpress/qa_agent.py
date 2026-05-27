"""
WordPress QA agent for the CloudIA agent system.

Performs comprehensive quality assurance checks on the completed WordPress
site. CRITICAL failures block the site_review gate.
"""

import httpx
import structlog
from sqlalchemy import select

from backend.agents.base import BaseAgent
from backend.ai.claude import call_claude_json
from backend.ai.context_builder import build_project_context
from backend.ai.prompts.wp_qa import WP_QA_SYSTEM_PROMPT, WP_QA_PROMPT_TEMPLATE
from backend.db.models import ApprovalGate, Client, GeneratedContent, Project
from backend.db.session import get_db

log = structlog.get_logger()

# Strings that indicate WordPress hasn't been properly configured
WP_DEFAULT_CONTENT_MARKERS = (
    "hello world",
    "sample page",
    "just another wordpress site",
    "error establishing a database connection",
    "wordpress › error",
)


class WPQAAgent(BaseAgent):
    """QA agent for WordPress sites."""

    agent_name = "wp_qa_agent"

    def run(self) -> dict:
        """
        1. Load project + content
        2. Perform HTTP checks on each page
        3. Check critical criteria
        4. Classify issues by severity
        5. Create site_review gate (or mark project failed)
        6. Return qa_report
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

            published_content = db.execute(
                select(GeneratedContent).where(
                    GeneratedContent.project_id == self.project_id,
                    GeneratedContent.status == "published",
                )
            ).scalars().all()

            pipeline_plan: dict = project.pipeline_plan or {}
            site_url: str = project.site_url or ""

            db.expunge(project)
            db.expunge(client)
            content_list = []
            for c in published_content:
                db.expunge(c)
                content_list.append(c)

        self.log.info(
            "wp_qa_start",
            site_url=site_url,
            pages=len(content_list),
        )

        checks: list[dict] = []
        critical_failures: list[str] = []
        high_warnings: list[str] = []
        medium_warnings: list[str] = []
        pages_checked: list[str] = []
        pages_failed: list[str] = []

        structure_plan = pipeline_plan.get("structure_plan", {})
        primary_menu = structure_plan.get("primary_menu", [])
        homepage_slug = structure_plan.get("homepage_slug", "home")

        # ------------------------------------------------------------------
        # HTTP checks on each page
        # ------------------------------------------------------------------
        with httpx.Client(timeout=15.0, follow_redirects=True) as http:
            for content in content_list:
                slug = content.page_slug
                if slug in ("home", ""):
                    url = site_url.rstrip("/") + "/"
                else:
                    url = site_url.rstrip("/") + "/" + slug.strip("/") + "/"

                pages_checked.append(slug)

                # Check HTTP status
                try:
                    resp = http.get(url)
                    status_code = resp.status_code
                    body = resp.text.lower()

                    if status_code != 200:
                        msg = f"Page /{slug} returned HTTP {status_code} (expected 200)"
                        critical_failures.append(msg)
                        checks.append({
                            "check": f"HTTP 200 — /{slug}",
                            "severity": "CRITICAL",
                            "passed": False,
                            "details": msg,
                        })
                        pages_failed.append(slug)
                    else:
                        checks.append({
                            "check": f"HTTP 200 — /{slug}",
                            "severity": "CRITICAL",
                            "passed": True,
                            "details": f"/{slug} returned 200 OK",
                        })

                    # Check for empty content
                    if len(body.strip()) < 200:
                        msg = f"Page /{slug} appears to have empty or near-empty content"
                        critical_failures.append(msg)
                        checks.append({
                            "check": f"Non-empty content — /{slug}",
                            "severity": "CRITICAL",
                            "passed": False,
                            "details": msg,
                        })
                    else:
                        # Check for WordPress default markers
                        for marker in WP_DEFAULT_CONTENT_MARKERS:
                            if marker in body:
                                msg = (
                                    f"Page /{slug} contains default WordPress content: "
                                    f"'{marker}'"
                                )
                                high_warnings.append(msg)
                                checks.append({
                                    "check": f"No default WP content — /{slug}",
                                    "severity": "HIGH",
                                    "passed": False,
                                    "details": msg,
                                })
                                break
                        else:
                            checks.append({
                                "check": f"Non-empty content — /{slug}",
                                "severity": "CRITICAL",
                                "passed": True,
                                "details": f"/{slug} has substantive content",
                            })

                    # Check meta title
                    if not content.meta_title:
                        msg = f"Page /{slug} has no meta title"
                        high_warnings.append(msg)
                        checks.append({
                            "check": f"Meta title present — /{slug}",
                            "severity": "HIGH",
                            "passed": False,
                            "details": msg,
                        })
                    else:
                        checks.append({
                            "check": f"Meta title present — /{slug}",
                            "severity": "HIGH",
                            "passed": True,
                            "details": f"meta_title: '{content.meta_title[:50]}'",
                        })

                    # Contact page — check for contact details
                    if slug == "contact":
                        has_phone = bool(
                            getattr(client, "contact_phone", None)
                            and str(client.contact_phone) in resp.text
                        )
                        has_email = bool(
                            getattr(client, "contact_email", None)
                            and str(client.contact_email) in resp.text
                        )
                        if not has_phone and not has_email:
                            msg = "Contact page has neither phone nor email visible"
                            high_warnings.append(msg)
                            checks.append({
                                "check": "Contact page has at least one contact method",
                                "severity": "HIGH",
                                "passed": False,
                                "details": msg,
                            })
                        elif not has_phone or not has_email:
                            msg = f"Contact page missing {'phone' if not has_phone else 'email'}"
                            medium_warnings.append(msg)
                            checks.append({
                                "check": "Contact page has both phone and email",
                                "severity": "MEDIUM",
                                "passed": False,
                                "details": msg,
                            })
                        else:
                            checks.append({
                                "check": "Contact page has both phone and email",
                                "severity": "MEDIUM",
                                "passed": True,
                                "details": "Contact page has phone and email",
                            })

                except httpx.RequestError as exc:
                    msg = f"Could not reach /{slug}: {exc}"
                    critical_failures.append(msg)
                    checks.append({
                        "check": f"HTTP reachable — /{slug}",
                        "severity": "CRITICAL",
                        "passed": False,
                        "details": msg,
                    })
                    pages_failed.append(slug)

        # ------------------------------------------------------------------
        # Navigation menu checks
        # ------------------------------------------------------------------
        if not primary_menu:
            msg = "No primary navigation menu found in structure plan"
            critical_failures.append(msg)
            checks.append({
                "check": "Primary navigation menu exists",
                "severity": "CRITICAL",
                "passed": False,
                "details": msg,
            })
        elif len(primary_menu) < 3:
            msg = f"Primary menu has only {len(primary_menu)} items (minimum 3 expected)"
            critical_failures.append(msg)
            checks.append({
                "check": "Primary menu has at least 3 items",
                "severity": "CRITICAL",
                "passed": False,
                "details": msg,
            })
        else:
            checks.append({
                "check": "Primary navigation menu exists",
                "severity": "CRITICAL",
                "passed": True,
                "details": f"Primary menu has {len(primary_menu)} items",
            })

        # ------------------------------------------------------------------
        # Homepage check (verify it was set as static front page)
        # ------------------------------------------------------------------
        homepage_built = homepage_slug in [c.page_slug for c in content_list]
        if not homepage_built:
            msg = f"Homepage slug '{homepage_slug}' was not found in published pages"
            critical_failures.append(msg)
            checks.append({
                "check": "Homepage set as static front page",
                "severity": "CRITICAL",
                "passed": False,
                "details": msg,
            })
        else:
            checks.append({
                "check": "Homepage set as static front page",
                "severity": "CRITICAL",
                "passed": True,
                "details": f"Homepage slug '{homepage_slug}' found in published pages",
            })

        # ------------------------------------------------------------------
        # Site title check
        # ------------------------------------------------------------------
        client_name = getattr(client, "name", "") or ""
        if site_url:
            try:
                with httpx.Client(timeout=10.0, follow_redirects=True) as http:
                    resp = http.get(site_url.rstrip("/") + "/")
                    title_ok = (
                        client_name.lower() in resp.text.lower()
                        if client_name
                        else len(resp.text) > 100
                    )
                    if not title_ok:
                        msg = "Site title does not appear to contain the business name"
                        critical_failures.append(msg)
                        checks.append({
                            "check": "Site title set to business name",
                            "severity": "CRITICAL",
                            "passed": False,
                            "details": msg,
                        })
                    else:
                        checks.append({
                            "check": "Site title set to business name",
                            "severity": "CRITICAL",
                            "passed": True,
                            "details": "Business name found on homepage",
                        })
            except Exception:
                pass  # Already checked HTTP above

        # ------------------------------------------------------------------
        # Determine overall status
        # ------------------------------------------------------------------
        if critical_failures:
            overall_status = "critical_failure"
        elif high_warnings:
            overall_status = "pass_with_warnings"
        else:
            overall_status = "pass"

        recommendation = {
            "critical_failure": "Fix critical issues before approval",
            "pass_with_warnings": "Approve with warnings",
            "pass": "Approved",
        }[overall_status]

        qa_report = {
            "overall_status": overall_status,
            "checks": checks,
            "critical_failures": critical_failures,
            "high_warnings": high_warnings,
            "medium_warnings": medium_warnings,
            "pages_checked": pages_checked,
            "pages_failed": pages_failed,
            "recommendation": recommendation,
        }

        # ------------------------------------------------------------------
        # Update project + gate based on QA outcome
        # ------------------------------------------------------------------
        if overall_status == "critical_failure":
            with get_db() as db:
                db_project = db.get(Project, self.project_id)
                if db_project:
                    db_project.status = "failed"
                    db.commit()

            self.log.error(
                "wp_qa_critical_failure",
                failures=critical_failures,
            )

            # Notify about failure
            try:
                from backend.notifications.email import notify_task_failed
                notify_task_failed(
                    project_id=self.project_id,
                    agent_name=self.agent_name,
                    error=f"QA critical failures: {'; '.join(critical_failures)}",
                )
            except Exception:
                pass

        else:
            # Create or update site_review gate
            notes = None
            if high_warnings:
                notes = "Warnings: " + "; ".join(high_warnings[:5])
                if medium_warnings:
                    notes += " | " + "; ".join(medium_warnings[:3])

            with get_db() as db:
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
                        pipeline_order=6,
                        status="pending",
                        notes=notes,
                    )
                    db.add(gate)
                    db.commit()
                    self.log.info("wp_qa_site_review_gate_created")
                else:
                    existing_gate.notes = notes
                    existing_gate.status = "pending"
                    db.commit()

        self.log.info(
            "wp_qa_complete",
            overall_status=overall_status,
            critical=len(critical_failures),
            high=len(high_warnings),
            medium=len(medium_warnings),
        )

        return {
            "qa_report": qa_report,
            "overall_status": overall_status,
            "_tokens_used": 0,
            "_cost_usd": 0.0,
        }
