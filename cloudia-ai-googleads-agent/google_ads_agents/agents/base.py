"""BaseAgent — all agents inherit from this class."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.orm import Session

import config
from ai.claude import ClaudeClient
from db.models import Account, AgentRun
from google_ads.client import AdsClient

logger = logging.getLogger(__name__)


@dataclass
class AgentRunResult:
    """Summary returned by every agent.execute() call."""

    agent_name: str
    account_id: int
    status: str = "success"
    tokens_used: int = 0
    cost_usd: float = 0.0
    decisions_generated: int = 0
    anomalies_found: int = 0
    summary: str = ""
    error: str = ""
    details: list[dict] = field(default_factory=list)


class BaseAgent:
    """Shared scaffolding for all agents.

    Handles run logging to agent_runs, calibration checks, and error capture.
    Subclasses implement execute().
    """

    name: str = "base"

    def __init__(self, ads_client: AdsClient, claude_client: ClaudeClient, db_session: Session) -> None:
        self.ads = ads_client
        self.claude = claude_client
        self.db = db_session

    def run(self, account: Account) -> AgentRunResult:
        """Entry point called by the orchestrator.

        Logs start, checks calibration, calls execute(), logs completion.
        """
        run_record = AgentRun(
            agent_name=self.name,
            account_id=account.id,
            started_at=datetime.now(timezone.utc),
            status="running",
        )
        self.db.add(run_record)
        self.db.commit()

        if account.status in (config.ACCOUNT_STATUS_PAUSED, config.ACCOUNT_STATUS_CHURNED):
            logger.info(
                "[%s] Skipping account %s — status is '%s'",
                self.name,
                account.client_name,
                account.status,
            )
            run_record.status = "skipped"
            run_record.completed_at = datetime.now(timezone.utc)
            run_record.summary = f"Account is {account.status} — skipping"
            self.db.commit()
            return AgentRunResult(
                agent_name=self.name,
                account_id=account.id,
                status="skipped",
                summary=f"Skipped — account status is '{account.status}'",
            )

        if self.is_calibrating(account):
            logger.info(
                "[%s] Skipping account %s — still in calibration period",
                self.name,
                account.client_name,
            )
            run_record.status = "skipped"
            run_record.completed_at = datetime.now(timezone.utc)
            run_record.summary = "Account still in 30-day calibration period"
            self.db.commit()
            return AgentRunResult(
                agent_name=self.name,
                account_id=account.id,
                status="skipped",
                summary="Skipped — calibration period active",
            )

        try:
            result = self.execute(account)
            run_record.status = result.status
            run_record.completed_at = datetime.now(timezone.utc)
            run_record.tokens_used = result.tokens_used
            run_record.cost_usd = result.cost_usd
            run_record.decisions_generated = result.decisions_generated
            run_record.anomalies_found = result.anomalies_found
            run_record.summary = result.summary
            self.db.commit()
            logger.info(
                "[%s] Completed for %s — %s",
                self.name,
                account.client_name,
                result.summary,
            )
            return result
        except Exception as exc:
            error_msg = str(exc)
            run_record.status = "failed"
            run_record.completed_at = datetime.now(timezone.utc)
            run_record.error = error_msg
            self.db.commit()
            logger.exception("[%s] Failed for account %s", self.name, account.client_name)
            raise

    def execute(self, account: Account) -> AgentRunResult:
        """Override in each agent subclass."""
        raise NotImplementedError

    def is_calibrating(self, account: Account) -> bool:
        """Return True if this account has not yet completed its 30-day calibration."""
        if account.baseline_set_at is None:
            return True
        age_days = (datetime.now(timezone.utc) - account.baseline_set_at.replace(tzinfo=timezone.utc)).days
        return age_days < config.CALIBRATION_DAYS
