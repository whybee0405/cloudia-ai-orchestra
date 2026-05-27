"""
Director agent for the CloudIA agent system.

Analyzes client brief, selects platform, creates the project and full pipeline
in the database, and queues the first Celery task.

Runs synchronously (not as a Celery task) — called from the API layer on
project creation.
"""

import structlog
from sqlalchemy import select

from backend.ai.claude import call_claude_json
from backend.ai.context_builder import build_project_context
from backend.ai.prompts.director import DIRECTOR_SYSTEM_PROMPT
from backend.db.models import (
    AgentTask,
    ApprovalGate,
    Client,
    Project,
)
from backend.db.session import get_db

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Pipeline definitions
# ---------------------------------------------------------------------------

WORDPRESS_PIPELINE: list[dict] = [
    {"agent_name": "content_agent",      "pipeline_order": 1, "celery_task": "run_content_agent"},
    {"agent_name": "media_agent",        "pipeline_order": 2, "celery_task": "run_media_agent"},
    {"agent_name": "wp_structure_agent", "pipeline_order": 3, "celery_task": "run_wp_structure_agent"},
    {"agent_name": "wp_builder_agent",   "pipeline_order": 4, "celery_task": "run_wp_builder_agent"},
    {"agent_name": "seo_agent",          "pipeline_order": 5, "celery_task": "run_seo_agent"},
    {"agent_name": "wp_qa_agent",        "pipeline_order": 6, "celery_task": "run_wp_qa_agent"},
]

SHOPIFY_PIPELINE: list[dict] = [
    {"agent_name": "content_agent",          "pipeline_order": 1, "celery_task": "run_content_agent"},
    {"agent_name": "media_agent",            "pipeline_order": 2, "celery_task": "run_media_agent"},
    {"agent_name": "shopify_structure_agent","pipeline_order": 3, "celery_task": "run_shopify_structure_agent"},
    {"agent_name": "shopify_builder_agent",  "pipeline_order": 4, "celery_task": "run_shopify_builder_agent"},
    {"agent_name": "shopify_theme_agent",    "pipeline_order": 5, "celery_task": "run_shopify_theme_agent"},
    {"agent_name": "seo_agent",              "pipeline_order": 6, "celery_task": "run_seo_agent"},
    {"agent_name": "shopify_qa_agent",       "pipeline_order": 7, "celery_task": "run_shopify_qa_agent"},
]

# ---------------------------------------------------------------------------
# Approval gate definitions — (after_pipeline_order, gate_name)
# ---------------------------------------------------------------------------

WORDPRESS_GATES: list[dict] = [
    {"gate_name": "content_review", "pipeline_order": 1},  # after content_agent
    {"gate_name": "site_review",    "pipeline_order": 6},  # after wp_qa_agent
]

SHOPIFY_GATES: list[dict] = [
    {"gate_name": "content_review", "pipeline_order": 1},  # after content_agent
    {"gate_name": "store_review",   "pipeline_order": 7},  # after shopify_qa_agent
]


class DirectorAgent:
    """Analyzes client brief, selects platform, creates pipeline tasks in DB."""

    def __init__(self, client_id: int, raw_brief: dict) -> None:
        self.client_id = client_id
        self.raw_brief = raw_brief
        self.log = log.bind(agent="director", client_id=client_id)

    def analyze(self) -> dict:
        """
        1. Load client from DB
        2. Build context
        3. Call Claude to determine platform + page list
        4. Create Project record (status: planned)
        5. Create AgentTask rows for the pipeline (status: pending)
        6. Create ApprovalGate rows at correct positions
        7. Queue first Celery task (run_content_agent)
        8. Return dict with project_id and platform info
        """
        # ------------------------------------------------------------------
        # 1. Load client
        # ------------------------------------------------------------------
        with get_db() as db:
            client = db.get(Client, self.client_id)
            if client is None:
                raise ValueError(f"Client {self.client_id} not found")
            # Copy to use outside session
            db.expunge(client)

        self.log.info("director_analyze_start", client_name=client.name)

        # ------------------------------------------------------------------
        # 2. Build a temporary project-like object for context
        # (we don't have a project yet — use a simple namespace)
        # ------------------------------------------------------------------
        class _TempProject:
            id = None
            platform = self.raw_brief.get("platform_hint", "wordpress")
            brief = self.raw_brief
            pipeline_plan = None

        context = build_project_context(client, _TempProject())

        # ------------------------------------------------------------------
        # 3. Call Claude
        # ------------------------------------------------------------------
        prompt = (
            f"{context}\n\n"
            "Based on the client brief above, produce the platform recommendation "
            "and pipeline plan JSON exactly as specified in your instructions.\n\n"
            f"Raw brief data: {self.raw_brief}"
        )

        self.log.info("director_calling_claude")
        plan, tokens, cost = call_claude_json(
            prompt=prompt,
            system=DIRECTOR_SYSTEM_PROMPT,
            max_tokens=2048,
        )

        platform: str = plan.get("platform", "wordpress")
        self.log.info(
            "director_claude_result",
            platform=platform,
            estimated_pages=plan.get("estimated_pages"),
            tokens=tokens,
            cost_usd=round(cost, 6),
        )

        # ------------------------------------------------------------------
        # 4. Handle ambiguous platform
        # ------------------------------------------------------------------
        if platform == "ambiguous":
            # Create project but DO NOT create pipeline tasks
            with get_db() as db:
                project = Project(
                    client_id=self.client_id,
                    platform="wordpress",  # placeholder
                    status="needs_input",
                    brief=self.raw_brief,
                    pipeline_plan=plan,
                )
                db.add(project)
                db.commit()
                db.refresh(project)
                project_id = project.id

            self.log.warning(
                "director_platform_ambiguous",
                reason=plan.get("ambiguity_reason"),
                project_id=project_id,
            )

            # Notify operator via WebSocket
            try:
                from backend.api.websocket import send_project_event
                send_project_event(
                    project_id=project_id,
                    event_type="platform_ambiguous",
                    data={
                        "reason": plan.get("ambiguity_reason"),
                        "message": "Platform selection requires operator input.",
                    },
                )
            except Exception as ws_exc:
                self.log.warning("websocket_notify_failed", error=str(ws_exc))

            return {
                "project_id": project_id,
                "platform": "ambiguous",
                "status": "needs_input",
                "ambiguity_reason": plan.get("ambiguity_reason"),
                "plan": plan,
            }

        # ------------------------------------------------------------------
        # 5. Create Project record
        # ------------------------------------------------------------------
        if platform not in ("wordpress", "shopify"):
            self.log.warning(
                "director_unknown_platform",
                platform=platform,
                falling_back_to="wordpress",
            )
            platform = "wordpress"

        pipeline_plan = {
            **plan,
            "platform": platform,
        }

        with get_db() as db:
            project = Project(
                client_id=self.client_id,
                platform=platform,
                status="planned",
                brief=self.raw_brief,
                pipeline_plan=pipeline_plan,
            )
            db.add(project)
            db.flush()  # get ID before creating tasks

            # --------------------------------------------------------------
            # 6. Create AgentTask rows
            # --------------------------------------------------------------
            pipeline = WORDPRESS_PIPELINE if platform == "wordpress" else SHOPIFY_PIPELINE
            task_ids: dict[int, int] = {}  # pipeline_order → task.id

            for step in pipeline:
                task = AgentTask(
                    project_id=project.id,
                    agent_name=step["agent_name"],
                    pipeline_order=step["pipeline_order"],
                    status="pending",
                    input_data={
                        "platform": platform,
                        "page_list": plan.get("page_list", []),
                        "pipeline_plan": pipeline_plan,
                    },
                    retry_count=0,
                )
                db.add(task)
                db.flush()
                task_ids[step["pipeline_order"]] = task.id

            # --------------------------------------------------------------
            # 6b. Create ApprovalGate rows
            # --------------------------------------------------------------
            gates = WORDPRESS_GATES if platform == "wordpress" else SHOPIFY_GATES
            gate_ids: dict[str, int] = {}

            for gate_def in gates:
                gate = ApprovalGate(
                    project_id=project.id,
                    gate_name=gate_def["gate_name"],
                    pipeline_order=gate_def["pipeline_order"],
                    status="pending",
                )
                db.add(gate)
                db.flush()
                gate_ids[gate_def["gate_name"]] = gate.id

            project_id = project.id
            first_task_id = task_ids[1]

            db.commit()

        self.log.info(
            "director_pipeline_created",
            project_id=project_id,
            platform=platform,
            task_count=len(pipeline),
            gate_count=len(gates),
        )

        # ------------------------------------------------------------------
        # 7. Queue the first Celery task (content_agent)
        # ------------------------------------------------------------------
        try:
            from backend.tasks.celery_app import celery_app
            celery_app.send_task(
                "run_content_agent",
                kwargs={"project_id": project_id, "task_id": first_task_id},
            )
            self.log.info(
                "director_first_task_queued",
                task="run_content_agent",
                project_id=project_id,
                task_id=first_task_id,
            )
        except Exception as queue_exc:
            # Don't fail the whole operation if queuing fails — operator can re-queue
            self.log.error("director_queue_failed", error=str(queue_exc))

        # ------------------------------------------------------------------
        # 8. Return summary
        # ------------------------------------------------------------------
        return {
            "project_id": project_id,
            "platform": platform,
            "status": "planned",
            "estimated_pages": plan.get("estimated_pages", 0),
            "page_list": plan.get("page_list", []),
            "requires_woocommerce": plan.get("requires_woocommerce", False),
            "requires_blog": plan.get("requires_blog", False),
            "task_count": len(pipeline),
            "first_task_id": first_task_id,
            "reasoning": plan.get("reasoning", ""),
        }
