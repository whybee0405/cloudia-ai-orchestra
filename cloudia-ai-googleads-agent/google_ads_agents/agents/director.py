"""Director agent — top of the agent hierarchy.

The Director coordinates all four specialist agents, running them in the
correct order with appropriate parallelism, then synthesises their reports
into a single holistic narrative via Claude.

Hierarchy
---------
Director
├── AnalysisDivision    (wraps AuditorAgent)
├── OptimizationDivision (wraps ManagerAgent + KeywordScoutAgent, parallel)
└── ReportingDivision   (wraps ReporterAgent)

Flow
----
1. Fetch all active accounts from the DB.
2. For each account:
   a. Run AnalysisDivision (Auditor).
   b. Run OptimizationDivision (Manager + KeywordScout in parallel threads).
   c. Optionally run ReportingDivision (Reporter — weekly cadence, flag-gated).
3. Each division produces a DivisionReport with its own summary, counts, and
   per-agent results.  Failures in one division never block others.
4. After all accounts are processed, Director calls Claude once to synthesise
   a cross-division holistic executive report.
5. Return a DirectorReport with all division reports attached.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

import config
from agents.auditor import AuditorAgent
from agents.base import AgentRunResult
from agents.keyword_scout import KeywordScoutAgent
from agents.manager import ManagerAgent
from agents.reporter import ReporterAgent
from ai.claude import ClaudeClient
from ai.prompts.director import DIRECTOR_SYSTEM_PROMPT
from db.models import Account
from google_ads.client import AdsClient

logger = logging.getLogger(__name__)


# ── Report dataclasses ────────────────────────────────────────────────────────

@dataclass
class AgentTaskResult:
    """The outcome of a single agent running for a single account."""

    agent_name: str
    account_id: int
    account_name: str
    status: str
    summary: str
    decisions_generated: int = 0
    anomalies_found: int = 0
    tokens_used: int = 0
    error: str = ""


@dataclass
class DivisionReport:
    """Aggregated report from one division across all accounts it processed."""

    division_name: str
    accounts_processed: int
    total_decisions: int
    total_anomalies: int
    total_tokens: int
    agent_results: list[AgentTaskResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        return (
            f"{self.division_name}: {self.accounts_processed} accounts, "
            f"{self.total_decisions} decisions, "
            f"{self.total_anomalies} anomalies, "
            f"{len(self.errors)} errors"
        )


@dataclass
class DirectorReport:
    """Holistic report produced by the Director after synthesising all divisions."""

    run_time: datetime
    accounts_processed: int
    division_reports: list[DivisionReport]
    executive_summary: str
    priority_actions: list[str]
    risk_flags: list[str]
    commendations: list[str]
    next_cycle_focus: str
    total_tokens: int
    total_cost_usd: float
    synthesis_tokens: int = 0

    @property
    def total_decisions(self) -> int:
        return sum(r.total_decisions for r in self.division_reports)

    @property
    def total_anomalies(self) -> int:
        return sum(r.total_anomalies for r in self.division_reports)


# ── Division agents ────────────────────────────────────────────────────────────

class AnalysisDivision:
    """Wraps AuditorAgent. Runs anomaly detection for a list of accounts.

    Reporting up: returns a DivisionReport with per-account AgentTaskResults.
    """

    name = "analysis"

    def __init__(self, ads_client: AdsClient, claude_client: ClaudeClient, db: Session) -> None:
        self._agent = AuditorAgent(ads_client, claude_client, db)

    def run(self, accounts: list[Account]) -> DivisionReport:
        """Run the Auditor for every account and aggregate the results."""
        logger.info("[director/analysis] Running Auditor for %d accounts", len(accounts))
        results: list[AgentTaskResult] = []
        errors: list[str] = []

        for account in accounts:
            try:
                run_result: AgentRunResult = self._agent.run(account)
                results.append(AgentTaskResult(
                    agent_name="auditor",
                    account_id=account.id,
                    account_name=account.client_name,
                    status=run_result.status,
                    summary=run_result.summary,
                    anomalies_found=run_result.anomalies_found,
                    tokens_used=run_result.tokens_used,
                ))
            except Exception as exc:
                msg = f"Auditor failed for '{account.client_name}': {exc}"
                logger.exception("[director/analysis] %s", msg)
                errors.append(msg)
                results.append(AgentTaskResult(
                    agent_name="auditor",
                    account_id=account.id,
                    account_name=account.client_name,
                    status="failed",
                    summary=msg,
                    error=str(exc),
                ))

        return DivisionReport(
            division_name="Analysis",
            accounts_processed=len(accounts),
            total_decisions=0,
            total_anomalies=sum(r.anomalies_found for r in results),
            total_tokens=sum(r.tokens_used for r in results),
            agent_results=results,
            errors=errors,
        )


class OptimizationDivision:
    """Wraps ManagerAgent and KeywordScoutAgent, running them in parallel per account.

    For each account, Manager (bid/budget) and KeywordScout (keyword discovery)
    are dispatched simultaneously using a thread pool. Both report back to this
    division before results are aggregated and returned to the Director.

    Reporting up: returns a DivisionReport with per-account, per-agent results.
    """

    name = "optimization"

    def __init__(self, ads_client: AdsClient, claude_client: ClaudeClient, db: Session) -> None:
        self._manager = ManagerAgent(ads_client, claude_client, db)
        self._scout = KeywordScoutAgent(ads_client, claude_client, db)

    def run(self, accounts: list[Account]) -> DivisionReport:
        """Run Manager and KeywordScout in parallel for every account."""
        logger.info(
            "[director/optimization] Running Manager + KeywordScout for %d accounts (parallel per account)",
            len(accounts),
        )
        results: list[AgentTaskResult] = []
        errors: list[str] = []

        for account in accounts:
            account_results = self._run_parallel_for_account(account)
            results.extend(account_results["results"])
            errors.extend(account_results["errors"])

        return DivisionReport(
            division_name="Optimization",
            accounts_processed=len(accounts),
            total_decisions=sum(r.decisions_generated for r in results),
            total_anomalies=0,
            total_tokens=sum(r.tokens_used for r in results),
            agent_results=results,
            errors=errors,
        )

    def _run_parallel_for_account(self, account: Account) -> dict[str, Any]:
        """Run Manager and KeywordScout in parallel threads for one account.

        Returns a dict with 'results' (list of AgentTaskResult) and 'errors'.
        """
        results: list[AgentTaskResult] = []
        errors: list[str] = []

        def run_manager() -> AgentTaskResult:
            run_result = self._manager.run(account)
            return AgentTaskResult(
                agent_name="manager",
                account_id=account.id,
                account_name=account.client_name,
                status=run_result.status,
                summary=run_result.summary,
                decisions_generated=run_result.decisions_generated,
                tokens_used=run_result.tokens_used,
            )

        def run_scout() -> AgentTaskResult:
            run_result = self._scout.run(account)
            return AgentTaskResult(
                agent_name="keyword_scout",
                account_id=account.id,
                account_name=account.client_name,
                status=run_result.status,
                summary=run_result.summary,
                decisions_generated=run_result.decisions_generated,
                tokens_used=run_result.tokens_used,
            )

        with ThreadPoolExecutor(max_workers=2, thread_name_prefix=f"opt-{account.id}") as pool:
            futures = {
                pool.submit(run_manager): "manager",
                pool.submit(run_scout): "keyword_scout",
            }
            for future in as_completed(futures):
                agent_name = futures[future]
                try:
                    results.append(future.result())
                    logger.debug(
                        "[director/optimization] %s completed for '%s'",
                        agent_name,
                        account.client_name,
                    )
                except Exception as exc:
                    msg = f"{agent_name} failed for '{account.client_name}': {exc}"
                    logger.exception("[director/optimization] %s", msg)
                    errors.append(msg)
                    results.append(AgentTaskResult(
                        agent_name=agent_name,
                        account_id=account.id,
                        account_name=account.client_name,
                        status="failed",
                        summary=msg,
                        error=str(exc),
                    ))

        return {"results": results, "errors": errors}


class ReportingDivision:
    """Wraps ReporterAgent. Generates weekly performance reports per account.

    Reporting up: returns a DivisionReport with per-account AgentTaskResults.
    """

    name = "reporting"

    def __init__(self, ads_client: AdsClient, claude_client: ClaudeClient, db: Session) -> None:
        self._agent = ReporterAgent(ads_client, claude_client, db)

    def run(self, accounts: list[Account]) -> DivisionReport:
        """Run the Reporter for every account and aggregate the results."""
        logger.info("[director/reporting] Running Reporter for %d accounts", len(accounts))
        results: list[AgentTaskResult] = []
        errors: list[str] = []

        for account in accounts:
            try:
                run_result: AgentRunResult = self._agent.run(account)
                results.append(AgentTaskResult(
                    agent_name="reporter",
                    account_id=account.id,
                    account_name=account.client_name,
                    status=run_result.status,
                    summary=run_result.summary,
                    tokens_used=run_result.tokens_used,
                ))
            except Exception as exc:
                msg = f"Reporter failed for '{account.client_name}': {exc}"
                logger.exception("[director/reporting] %s", msg)
                errors.append(msg)
                results.append(AgentTaskResult(
                    agent_name="reporter",
                    account_id=account.id,
                    account_name=account.client_name,
                    status="failed",
                    summary=msg,
                    error=str(exc),
                ))

        return DivisionReport(
            division_name="Reporting",
            accounts_processed=len(accounts),
            total_decisions=0,
            total_anomalies=0,
            total_tokens=sum(r.tokens_used for r in results),
            agent_results=results,
            errors=errors,
        )


# ── Director ──────────────────────────────────────────────────────────────────

class DirectorAgent:
    """Top-level coordinator of the entire agent workforce.

    The Director delegates to three divisions:
      - AnalysisDivision (Auditor)
      - OptimizationDivision (Manager + KeywordScout in parallel)
      - ReportingDivision (Reporter)

    After all divisions complete, Director synthesises their reports into a
    single holistic executive narrative using Claude.

    The Creator agent is intentionally excluded from the Director's hierarchy —
    it is always triggered on-demand via the API, never scheduled.
    """

    name = "director"

    def __init__(
        self,
        ads_client: AdsClient,
        claude_client: ClaudeClient,
        db_session: Session,
    ) -> None:
        self.claude = claude_client
        self.db = db_session
        self._analysis = AnalysisDivision(ads_client, claude_client, db_session)
        self._optimization = OptimizationDivision(ads_client, claude_client, db_session)
        self._reporting = ReportingDivision(ads_client, claude_client, db_session)

    def run_full_cycle(
        self,
        accounts: list[Account],
        include_reporting: bool = False,
    ) -> DirectorReport:
        """Execute a full analysis + optimization cycle across all accounts.

        Args:
            accounts: List of Account ORM rows to process.
            include_reporting: When True, the Reporting division is also run
                (intended for the weekly Monday 08:00 cycle only).

        Returns:
            DirectorReport containing all division reports and Claude's synthesis.
        """
        run_time = datetime.now(timezone.utc)
        logger.info(
            "[director] Starting full cycle for %d accounts (reporting=%s)",
            len(accounts),
            include_reporting,
        )

        division_reports: list[DivisionReport] = []

        # ── 1. Analysis Division ─────────────────────────────────────────────
        analysis_report = self._analysis.run(accounts)
        division_reports.append(analysis_report)
        logger.info("[director] Analysis complete: %s", analysis_report.summary)

        # ── 2. Optimization Division (Manager + KeywordScout in parallel) ────
        optimization_report = self._optimization.run(accounts)
        division_reports.append(optimization_report)
        logger.info("[director] Optimization complete: %s", optimization_report.summary)

        # ── 3. Reporting Division (weekly only) ──────────────────────────────
        if include_reporting:
            reporting_report = self._reporting.run(accounts)
            division_reports.append(reporting_report)
            logger.info("[director] Reporting complete: %s", reporting_report.summary)

        # ── 4. Synthesise reports via Claude ─────────────────────────────────
        synthesis, synthesis_tokens = self._synthesise(division_reports, accounts)

        total_tokens = sum(r.total_tokens for r in division_reports) + synthesis_tokens
        total_cost = self.claude.estimate_cost_usd(total_tokens)

        report = DirectorReport(
            run_time=run_time,
            accounts_processed=len(accounts),
            division_reports=division_reports,
            executive_summary=synthesis.get("executive_summary", ""),
            priority_actions=synthesis.get("priority_actions", []),
            risk_flags=synthesis.get("risk_flags", []),
            commendations=synthesis.get("commendations", []),
            next_cycle_focus=synthesis.get("next_cycle_focus", ""),
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            synthesis_tokens=synthesis_tokens,
        )

        logger.info(
            "[director] Full cycle complete — %d accounts, %d decisions, "
            "%d anomalies, %.4f USD",
            report.accounts_processed,
            report.total_decisions,
            report.total_anomalies,
            report.total_cost_usd,
        )

        return report

    def run_analysis_only(self, accounts: list[Account]) -> DirectorReport:
        """Run only the Analysis division — used by the 6-hourly auditor schedule."""
        run_time = datetime.now(timezone.utc)
        logger.info("[director] Running analysis-only cycle for %d accounts", len(accounts))

        analysis_report = self._analysis.run(accounts)
        synthesis, synthesis_tokens = self._synthesise([analysis_report], accounts)

        total_tokens = analysis_report.total_tokens + synthesis_tokens
        return DirectorReport(
            run_time=run_time,
            accounts_processed=len(accounts),
            division_reports=[analysis_report],
            executive_summary=synthesis.get("executive_summary", ""),
            priority_actions=synthesis.get("priority_actions", []),
            risk_flags=synthesis.get("risk_flags", []),
            commendations=synthesis.get("commendations", []),
            next_cycle_focus=synthesis.get("next_cycle_focus", ""),
            total_tokens=total_tokens,
            total_cost_usd=self.claude.estimate_cost_usd(total_tokens),
            synthesis_tokens=synthesis_tokens,
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    def _synthesise(
        self,
        division_reports: list[DivisionReport],
        accounts: list[Account],
    ) -> tuple[dict, int]:
        """Ask Claude to synthesise division reports into a holistic narrative.

        Args:
            division_reports: All completed division reports.
            accounts: The accounts that were processed.

        Returns:
            Tuple of (synthesis_dict, tokens_used). Falls back to an empty
            synthesis dict on Claude failure rather than propagating the error.
        """
        user_message = _build_director_user_message(division_reports, accounts)

        try:
            result, tokens = self.claude.complete_json(
                system_prompt=DIRECTOR_SYSTEM_PROMPT,
                user_message=user_message,
                max_tokens=2048,
            )
            logger.debug("[director] Synthesis complete (%d tokens)", tokens)
            return result, tokens
        except Exception as exc:
            logger.exception("[director] Claude synthesis failed: %s", exc)
            return {
                "executive_summary": "Director synthesis unavailable — see individual division reports.",
                "priority_actions": [],
                "risk_flags": [],
                "commendations": [],
                "next_cycle_focus": "Review division reports manually.",
            }, 0


# ── User message builder ───────────────────────────────────────────────────────

def _build_director_user_message(
    division_reports: list[DivisionReport],
    accounts: list[Account],
) -> str:
    """Build the user message Claude uses to synthesise the Director report.

    Args:
        division_reports: All completed DivisionReport objects.
        accounts: The Account rows that were processed.

    Returns:
        A structured multi-section string ready to send to Claude.
    """
    account_list = ", ".join(a.client_name for a in accounts) or "no accounts"

    sections = [
        f"=== DIRECTOR SYNTHESIS REQUEST ===",
        f"Accounts processed: {len(accounts)} ({account_list})",
        f"Cycle time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]

    for div in division_reports:
        sections.append(f"=== {div.division_name.upper()} DIVISION REPORT ===")
        sections.append(f"Accounts: {div.accounts_processed}")
        sections.append(f"Decisions queued: {div.total_decisions}")
        sections.append(f"Anomalies detected: {div.total_anomalies}")
        if div.errors:
            sections.append(f"Errors: {len(div.errors)}")
            for err in div.errors[:3]:
                sections.append(f"  - {err}")

        sections.append("")
        sections.append("Per-account results:")
        for res in div.agent_results:
            status_flag = "✓" if res.status in ("success", "skipped") else "✗"
            sections.append(
                f"  {status_flag} [{res.agent_name}] {res.account_name}: {res.summary[:120]}"
            )
        sections.append("")

    sections.append("=== INSTRUCTIONS ===")
    sections.append(
        "Synthesise the above into a single executive report. "
        "Focus on cross-division insights, contradictions, and the most critical actions."
    )

    return "\n".join(sections)
