"""Entry point — APScheduler BlockingScheduler + FastAPI in a background thread."""

import logging
import sys
import threading

import uvicorn
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

import config
from api.app import app
from ai.claude import ClaudeClient
from db.session import get_session
from google_ads.client import AdsClient
from orchestrator import Orchestrator

# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ── Client / session construction ──────────────────────────────────────────────

def _build_orchestrator() -> Orchestrator:
    """Construct fresh clients and a DB session and return a ready Orchestrator."""
    ads_client = AdsClient()
    claude_client = ClaudeClient()
    db_session = get_session()
    return Orchestrator(ads_client, claude_client, db_session)


# ── Scheduled job wrappers ─────────────────────────────────────────────────────
# Each wrapper creates its own Orchestrator so that DB sessions are not shared
# across scheduler threads.

def _run_auditor() -> None:
    logger.info("[scheduler] Auditor job triggered")
    orchestrator = _build_orchestrator()
    try:
        orchestrator.run_auditor()
    finally:
        orchestrator.db.close()


def _run_manager() -> None:
    logger.info("[scheduler] Manager job triggered")
    orchestrator = _build_orchestrator()
    try:
        orchestrator.run_manager()
    finally:
        orchestrator.db.close()


def _run_reporter() -> None:
    logger.info("[scheduler] Reporter job triggered")
    orchestrator = _build_orchestrator()
    try:
        orchestrator.run_reporter()
    finally:
        orchestrator.db.close()


def _run_keyword_scout() -> None:
    logger.info("[scheduler] KeywordScout job triggered")
    orchestrator = _build_orchestrator()
    try:
        orchestrator.run_keyword_scout()
    finally:
        orchestrator.db.close()


# ── FastAPI background thread ──────────────────────────────────────────────────

def _start_api_server() -> None:
    """Start the FastAPI/uvicorn server in a daemon thread.

    The thread is daemonised so it exits automatically when the main process
    shuts down (e.g. on KeyboardInterrupt stopping the scheduler).
    """
    api_thread = threading.Thread(
        target=uvicorn.run,
        kwargs={
            "app": app,
            "host": config.API_HOST,
            "port": config.API_PORT,
        },
        daemon=True,
        name="uvicorn-api",
    )
    api_thread.start()
    logger.info(
        "[main] FastAPI server started on http://%s:%d",
        config.API_HOST,
        config.API_PORT,
    )


# ── Scheduler setup ────────────────────────────────────────────────────────────

def _build_scheduler() -> BlockingScheduler:
    """Create and configure the APScheduler BlockingScheduler.

    Jobs:
        auditor       — every N hours (AUDITOR_INTERVAL_HOURS)
        manager       — daily at MANAGER_HOUR:00
        reporter      — every Monday at REPORTER_HOUR:00
        keyword_scout — every Sunday at KEYWORD_SCOUT_HOUR:00

    Returns:
        Configured BlockingScheduler (not yet started).
    """
    scheduler = BlockingScheduler(timezone="Africa/Johannesburg")

    scheduler.add_job(
        _run_auditor,
        trigger=IntervalTrigger(hours=config.AUDITOR_INTERVAL_HOURS),
        id="auditor",
        name="Auditor — anomaly detection",
        max_instances=1,
        coalesce=True,
    )

    scheduler.add_job(
        _run_manager,
        trigger=CronTrigger(hour=config.MANAGER_HOUR, minute=0),
        id="manager",
        name="Manager — bid & budget optimisation",
        max_instances=1,
        coalesce=True,
    )

    scheduler.add_job(
        _run_reporter,
        trigger=CronTrigger(
            day_of_week=config.REPORTER_DAY_OF_WEEK,
            hour=config.REPORTER_HOUR,
            minute=0,
        ),
        id="reporter",
        name="Reporter — weekly performance report",
        max_instances=1,
        coalesce=True,
    )

    scheduler.add_job(
        _run_keyword_scout,
        trigger=CronTrigger(
            day_of_week=config.KEYWORD_SCOUT_DAY_OF_WEEK,
            hour=config.KEYWORD_SCOUT_HOUR,
            minute=0,
        ),
        id="keyword_scout",
        name="KeywordScout — keyword opportunity mining",
        max_instances=1,
        coalesce=True,
    )

    return scheduler


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    """Bootstrap the CloudIA Google Ads Agent system.

    1. Starts the FastAPI server in a daemon background thread.
    2. Builds the APScheduler BlockingScheduler with all four agent jobs.
    3. Logs every scheduled job at startup.
    4. Blocks in the scheduler until interrupted.
    5. Catches KeyboardInterrupt and shuts down gracefully.
    """
    logger.info(
        "CloudIA Google Ads Agent starting up (environment=%s)", config.ENVIRONMENT
    )

    # Start FastAPI in background
    _start_api_server()
    logger.info(
        "[main] API available at http://%s:%d/docs", config.API_HOST, config.API_PORT
    )

    # Build scheduler
    scheduler = _build_scheduler()

    # Log all scheduled jobs on startup
    logger.info("[main] Scheduled jobs:")
    for job in scheduler.get_jobs():
        logger.info(
            "[main]   %-20s  trigger=%s", job.id, job.trigger
        )

    # Start scheduler (blocks until shutdown)
    try:
        logger.info("[main] Scheduler starting — press Ctrl+C to stop")
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("[main] KeyboardInterrupt received — shutting down gracefully")
        scheduler.shutdown(wait=False)
        logger.info("[main] Scheduler stopped. Goodbye.")
        sys.exit(0)


if __name__ == "__main__":
    main()
