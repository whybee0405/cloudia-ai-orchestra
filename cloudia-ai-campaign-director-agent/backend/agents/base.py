"""BaseAgent — shared logging, token tracking, DB task management, error handling."""
import logging
import time
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from backend.db.models import AgentTask

logger = logging.getLogger(__name__)


class AgentError(Exception):
    """Raised when an agent encounters a non-retryable error."""


class AgentRetryError(Exception):
    """Raised when an agent wants Celery to retry the task."""


class BaseAgent:
    """
    All agents inherit from this. Provides:
    - DB task record lifecycle (create → in_progress → completed/failed)
    - Token and cost tracking
    - Structured logging
    """

    name: str = "base_agent"

    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(f"agent.{self.name}")
        self._task_record: Optional[AgentTask] = None
        self._total_tokens: int = 0
        self._total_cost: float = 0.0

    def _start_task(self, campaign_id: int, calendar_id: Optional[int], input_data: dict, pipeline_order: int = 0) -> AgentTask:
        task = AgentTask(
            campaign_id=campaign_id,
            calendar_id=calendar_id,
            agent_name=self.name,
            pipeline_order=pipeline_order,
            status="running",
            input_data=input_data,
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        self._task_record = task
        self.logger.info("Task %d started: campaign=%d", task.id, campaign_id)
        return task

    def _complete_task(self, output_data: dict) -> None:
        if not self._task_record:
            return
        self._task_record.status = "completed"
        self._task_record.output_data = output_data
        self._task_record.tokens_used = self._total_tokens
        self._task_record.cost_usd = round(self._total_cost, 6)
        self._task_record.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.logger.info(
            "Task %d completed: tokens=%d cost=$%.6f",
            self._task_record.id, self._total_tokens, self._total_cost,
        )

    def _fail_task(self, error: str) -> None:
        if not self._task_record:
            return
        self._task_record.status = "failed"
        self._task_record.error = error
        self._task_record.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.logger.error("Task %d failed: %s", self._task_record.id, error)

    def _track_tokens(self, input_tokens: int, output_tokens: int, cost_usd: float) -> None:
        self._total_tokens += input_tokens + output_tokens
        self._total_cost += cost_usd

    def run(self, *args, **kwargs):
        raise NotImplementedError
