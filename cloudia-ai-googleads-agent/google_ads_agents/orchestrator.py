"""Orchestrator — loops all agents across all active accounts."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from agents.auditor import AuditorAgent
from agents.manager import ManagerAgent
from agents.reporter import ReporterAgent
from agents.keyword_scout import KeywordScoutAgent
from ai.claude import ClaudeClient
from db.models import Account
from google_ads.client import AdsClient

logger = logging.getLogger(__name__)


class Orchestrator:
    """Coordinates all scheduled agents, iterating them across every active account.

    Each agent run method follows the same pattern:
    - Fetch all active accounts from the database
    - Call agent.run(account) for each one
    - Log start and completion at the account level
    - Catch and log per-account exceptions without stopping the loop

    This means a single broken account never prevents the others from being
    processed — failures are isolated, logged, and the loop continues.
    """

    def __init__(
        self,
        ads_client: AdsClient,
        claude_client: ClaudeClient,
        db_session: Session,
    ) -> None:
        self.ads = ads_client
        self.claude = claude_client
        self.db = db_session

        # Instantiate all four scheduled agents once at construction time
        self.auditor = AuditorAgent(ads_client, claude_client, db_session)
        self.manager = ManagerAgent(ads_client, claude_client, db_session)
        self.reporter = ReporterAgent(ads_client, claude_client, db_session)
        self.keyword_scout = KeywordScoutAgent(ads_client, claude_client, db_session)

    # ── Account fetching ───────────────────────────────────────────────────────

    def get_active_accounts(self) -> list[Account]:
        """Return all Account rows whose status is 'active'.

        Returns:
            List of Account ORM objects with status='active'.
        """
        stmt = select(Account).where(Account.status == "active")
        accounts: list[Account] = list(self.db.scalars(stmt).all())
        logger.debug("Found %d active accounts", len(accounts))
        return accounts

    # ── Per-agent run methods ──────────────────────────────────────────────────

    def run_auditor(self) -> None:
        """Run the AuditorAgent for every active account.

        Logs start and completion for each account. Exceptions are caught and
        logged per account; the loop continues regardless of individual failures.
        """
        logger.info("[orchestrator] Starting auditor run across all active accounts")
        accounts = self.get_active_accounts()

        for account in accounts:
            logger.info(
                "[orchestrator] Running auditor for account '%s' (id=%d)",
                account.client_name,
                account.id,
            )
            try:
                result = self.auditor.run(account)
                logger.info(
                    "[orchestrator] Auditor completed for '%s' — status=%s summary=%s",
                    account.client_name,
                    result.status,
                    result.summary,
                )
            except Exception:
                logger.exception(
                    "[orchestrator] Auditor failed for account '%s' (id=%d) — continuing",
                    account.client_name,
                    account.id,
                )

        logger.info(
            "[orchestrator] Auditor run complete (%d accounts processed)", len(accounts)
        )

    def run_manager(self) -> None:
        """Run the ManagerAgent for every active account.

        Logs start and completion for each account. Exceptions are caught and
        logged per account; the loop continues regardless of individual failures.
        """
        logger.info("[orchestrator] Starting manager run across all active accounts")
        accounts = self.get_active_accounts()

        for account in accounts:
            logger.info(
                "[orchestrator] Running manager for account '%s' (id=%d)",
                account.client_name,
                account.id,
            )
            try:
                result = self.manager.run(account)
                logger.info(
                    "[orchestrator] Manager completed for '%s' — status=%s summary=%s",
                    account.client_name,
                    result.status,
                    result.summary,
                )
            except Exception:
                logger.exception(
                    "[orchestrator] Manager failed for account '%s' (id=%d) — continuing",
                    account.client_name,
                    account.id,
                )

        logger.info(
            "[orchestrator] Manager run complete (%d accounts processed)", len(accounts)
        )

    def run_reporter(self) -> None:
        """Run the ReporterAgent for every active account.

        Logs start and completion for each account. Exceptions are caught and
        logged per account; the loop continues regardless of individual failures.
        """
        logger.info("[orchestrator] Starting reporter run across all active accounts")
        accounts = self.get_active_accounts()

        for account in accounts:
            logger.info(
                "[orchestrator] Running reporter for account '%s' (id=%d)",
                account.client_name,
                account.id,
            )
            try:
                result = self.reporter.run(account)
                logger.info(
                    "[orchestrator] Reporter completed for '%s' — status=%s summary=%s",
                    account.client_name,
                    result.status,
                    result.summary,
                )
            except Exception:
                logger.exception(
                    "[orchestrator] Reporter failed for account '%s' (id=%d) — continuing",
                    account.client_name,
                    account.id,
                )

        logger.info(
            "[orchestrator] Reporter run complete (%d accounts processed)", len(accounts)
        )

    def run_keyword_scout(self) -> None:
        """Run the KeywordScoutAgent for every active account.

        Logs start and completion for each account. Exceptions are caught and
        logged per account; the loop continues regardless of individual failures.
        """
        logger.info(
            "[orchestrator] Starting keyword_scout run across all active accounts"
        )
        accounts = self.get_active_accounts()

        for account in accounts:
            logger.info(
                "[orchestrator] Running keyword_scout for account '%s' (id=%d)",
                account.client_name,
                account.id,
            )
            try:
                result = self.keyword_scout.run(account)
                logger.info(
                    "[orchestrator] KeywordScout completed for '%s' — status=%s summary=%s",
                    account.client_name,
                    result.status,
                    result.summary,
                )
            except Exception:
                logger.exception(
                    "[orchestrator] KeywordScout failed for account '%s' (id=%d) — continuing",
                    account.client_name,
                    account.id,
                )

        logger.info(
            "[orchestrator] KeywordScout run complete (%d accounts processed)",
            len(accounts),
        )
