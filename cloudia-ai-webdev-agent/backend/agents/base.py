"""
Base agent class for the CloudIA agent system.

Handles: task status updates, error logging, token tracking, retry counting.
All agent classes inherit from BaseAgent.
"""

from datetime import datetime, UTC

import structlog

from backend.db.models import AgentTask, Project
from backend.db.session import get_db

log = structlog.get_logger()


class BaseAgent:
    """Base class for all CloudIA agents.

    Handles: task status updates, error logging, token tracking, retry counting.
    """

    agent_name: str = "base"

    def __init__(self, project_id: int, task_id: int) -> None:
        self.project_id = project_id
        self.task_id = task_id
        self.log = log.bind(
            agent=self.agent_name,
            project_id=project_id,
            task_id=task_id,
        )

    # ------------------------------------------------------------------
    # Status management
    # ------------------------------------------------------------------

    def mark_running(self) -> None:
        """Set task status to 'running' and record started_at."""
        with get_db() as db:
            task = db.get(AgentTask, self.task_id)
            if task is None:
                raise RuntimeError(
                    f"AgentTask {self.task_id} not found for project {self.project_id}"
                )
            task.status = "running"
            task.started_at = datetime.now(UTC)
            db.commit()
        self.log.info("agent_running")

    def mark_completed(
        self,
        output_data: dict,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        """Set task status to 'completed', store output, record costs."""
        with get_db() as db:
            task = db.get(AgentTask, self.task_id)
            if task is None:
                raise RuntimeError(
                    f"AgentTask {self.task_id} not found for project {self.project_id}"
                )
            task.status = "completed"
            task.output_data = output_data
            task.tokens_used = tokens_used
            task.cost_usd = cost_usd
            task.completed_at = datetime.now(UTC)
            db.commit()
        self.log.info(
            "agent_completed",
            tokens_used=tokens_used,
            cost_usd=round(cost_usd, 6),
        )

    def mark_failed(self, error: str) -> None:
        """Set task status to 'failed', store error, increment retry_count."""
        with get_db() as db:
            task = db.get(AgentTask, self.task_id)
            if task is None:
                self.log.error("agent_task_not_found_on_fail", error=error)
                return
            task.status = "failed"
            task.error = error
            task.retry_count = (task.retry_count or 0) + 1
            task.completed_at = datetime.now(UTC)
            db.commit()
        self.log.error("agent_failed", error=error[:500])

        # Best-effort failure notification — never let this crash the agent
        try:
            from backend.notifications.email import notify_task_failed
            notify_task_failed(
                project_id=self.project_id,
                agent_name=self.agent_name,
                error=error,
            )
        except Exception as notify_exc:
            self.log.warning("failure_notification_error", error=str(notify_exc))

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def get_project(self) -> Project:
        """Load project from DB."""
        with get_db() as db:
            project = db.get(Project, self.project_id)
            if project is None:
                raise RuntimeError(f"Project {self.project_id} not found")
            # Detach from session so caller can use it outside the context
            db.expunge(project)
            return project

    def get_task(self) -> AgentTask:
        """Load this agent's task from DB."""
        with get_db() as db:
            task = db.get(AgentTask, self.task_id)
            if task is None:
                raise RuntimeError(
                    f"AgentTask {self.task_id} not found for project {self.project_id}"
                )
            db.expunge(task)
            return task

    # ------------------------------------------------------------------
    # Main entry points
    # ------------------------------------------------------------------

    def run(self) -> dict:
        """Override in subclasses. Returns output_data dict.

        Subclasses may include '_tokens_used' and '_cost_usd' keys in the
        returned dict — execute() will pop these before storing output_data.
        """
        raise NotImplementedError(
            f"Agent '{self.agent_name}' must implement run()"
        )

    def execute(self) -> dict:
        """Called by Celery task. Wraps run() with status management.

        Returns the output_data dict (without internal bookkeeping keys).
        """
        try:
            self.mark_running()
            result = self.run()
            # Pop internal bookkeeping keys before storing output
            tokens_used: int = result.pop("_tokens_used", 0)
            cost_usd: float = result.pop("_cost_usd", 0.0)
            self.mark_completed(
                output_data=result,
                tokens_used=tokens_used,
                cost_usd=cost_usd,
            )
            return result
        except Exception as exc:
            self.mark_failed(str(exc))
            raise
