"""FastAPI route handlers for the CloudIA Google Ads Agent API.

All mutation routes follow the human-in-the-loop pattern:
- Agent decisions land in approval_queue with status='pending'
- A human approves or rejects via /queue/{item_id}/approve|reject
- Only approved items can be executed via /queue/{item_id}/execute

Routes
------
GET  /accounts                          — list all accounts
GET  /queue                             — list pending queue items (optional ?account_id=N)
GET  /queue/{item_id}                   — get single queue item
POST /queue/{item_id}/approve           — approve a pending item
POST /queue/{item_id}/reject            — reject a pending item
POST /queue/{item_id}/execute           — execute an approved item via Google Ads API
POST /campaigns/create                  — trigger Creator agent from a brief
GET  /audit                             — list audit log entries
POST /accounts/{account_id}/baseline   — manually set account baseline metrics
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from agents.creator import CreatorAgent
from ai.claude import ClaudeClient
from api.schemas import (
    AccountResponse,
    AuditLogResponse,
    BaselineRequest,
    CampaignBriefRequest,
    CreateCampaignResponse,
    QueueActionRequest,
    QueueItemResponse,
)
from db.models import Account, AuditLog, ApprovalQueue
from db.queue import (
    approve_item,
    get_item_by_id,
    get_pending_items,
    reject_item,
)
from db.session import get_db
from google_ads.client import AdsClient
from google_ads.executor import Executor

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Dependency helpers ─────────────────────────────────────────────────────────

def _get_ads_client() -> AdsClient:
    """Instantiate and return the Google Ads client. Used as a FastAPI dependency."""
    return AdsClient()


def _get_claude_client() -> ClaudeClient:
    """Instantiate and return the Claude client. Used as a FastAPI dependency."""
    return ClaudeClient()


def _get_account_or_404(account_id: int, db: Session) -> Account:
    """Fetch an account by primary key or raise HTTP 404.

    Args:
        account_id: Primary key of the Account to fetch.
        db: Active SQLAlchemy session.

    Returns:
        The Account ORM row.

    Raises:
        HTTPException: 404 if the account does not exist.
    """
    stmt = select(Account).where(Account.id == account_id)
    account = db.scalars(stmt).first()
    if account is None:
        raise HTTPException(status_code=404, detail=f"Account id={account_id} not found")
    return account


def _get_queue_item_or_404(item_id: int, db: Session) -> ApprovalQueue:
    """Fetch a queue item by primary key or raise HTTP 404.

    Args:
        item_id: Primary key of the ApprovalQueue row.
        db: Active SQLAlchemy session.

    Returns:
        The ApprovalQueue ORM row.

    Raises:
        HTTPException: 404 if the item does not exist.
    """
    item = get_item_by_id(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Queue item id={item_id} not found")
    return item


# ── Account routes ─────────────────────────────────────────────────────────────

@router.get(
    "/accounts",
    response_model=list[AccountResponse],
    summary="List all accounts",
    tags=["Accounts"],
)
def list_accounts(
    db: Session = Depends(get_db),
) -> list[Account]:
    """Return all registered client accounts ordered by client name.

    Returns:
        List of AccountResponse objects for every row in the accounts table.
    """
    stmt = select(Account).order_by(Account.client_name)
    accounts = list(db.scalars(stmt).all())
    logger.debug("[routes] list_accounts: returning %d accounts", len(accounts))
    return accounts


@router.post(
    "/accounts/{account_id}/baseline",
    response_model=AccountResponse,
    summary="Manually set baseline metrics for an account",
    tags=["Accounts"],
)
def set_account_baseline(
    account_id: int,
    body: BaselineRequest,
    db: Session = Depends(get_db),
) -> Account:
    """Manually update one or more baseline metrics for an account.

    Only the fields present in the request body are updated. After update,
    baseline_set_at is always set to the current UTC timestamp, which clears
    the calibration flag and makes the account eligible for agent processing.

    Args:
        account_id: Primary key of the account to update.
        body: Partial baseline values (ctr, cvr, cpc, cpa, roas — all optional).

    Returns:
        Updated AccountResponse.

    Raises:
        HTTPException: 404 if the account does not exist.
    """
    account = _get_account_or_404(account_id, db)

    if body.ctr is not None:
        account.baseline_ctr = body.ctr
    if body.cvr is not None:
        account.baseline_cvr = body.cvr
    if body.cpc is not None:
        account.baseline_cpc = body.cpc
    if body.cpa is not None:
        account.baseline_cpa = body.cpa
    if body.roas is not None:
        account.baseline_roas = body.roas

    account.baseline_set_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(account)

    logger.info(
        "[routes] set_account_baseline: updated baseline for account id=%d (%s)",
        account.id,
        account.client_name,
    )
    return account


# ── Queue routes ───────────────────────────────────────────────────────────────

@router.get(
    "/queue",
    response_model=list[QueueItemResponse],
    summary="List pending queue items",
    tags=["Approval Queue"],
)
def list_queue_items(
    account_id: int | None = Query(None, description="Filter by account ID"),
    db: Session = Depends(get_db),
) -> list[ApprovalQueue]:
    """Return all pending approval queue items, newest first.

    Args:
        account_id: When supplied, only items for this account are returned.

    Returns:
        List of QueueItemResponse objects with status='pending'.
    """
    items = get_pending_items(db, account_id=account_id)
    logger.debug(
        "[routes] list_queue_items: returning %d items (account_id=%s)",
        len(items),
        account_id,
    )
    return items


@router.get(
    "/queue/{item_id}",
    response_model=QueueItemResponse,
    summary="Get a single queue item",
    tags=["Approval Queue"],
)
def get_queue_item(
    item_id: int,
    db: Session = Depends(get_db),
) -> ApprovalQueue:
    """Return a single approval queue item by ID.

    Args:
        item_id: Primary key of the ApprovalQueue row.

    Returns:
        QueueItemResponse for the requested item.

    Raises:
        HTTPException: 404 if the item does not exist.
    """
    return _get_queue_item_or_404(item_id, db)


@router.post(
    "/queue/{item_id}/approve",
    response_model=QueueItemResponse,
    summary="Approve a pending queue item",
    tags=["Approval Queue"],
)
def approve_queue_item(
    item_id: int,
    body: QueueActionRequest,
    db: Session = Depends(get_db),
) -> ApprovalQueue:
    """Mark a pending queue item as approved.

    The item must currently have status='pending'. After approval it moves to
    status='approved' and is eligible for execution via /queue/{item_id}/execute.

    Args:
        item_id: Primary key of the ApprovalQueue row to approve.
        body: Must contain reviewed_by (email or username of the approver).

    Returns:
        Updated QueueItemResponse with status='approved'.

    Raises:
        HTTPException: 404 if the item does not exist.
        HTTPException: 409 if the item is not currently pending.
    """
    _get_queue_item_or_404(item_id, db)  # raises 404 before queue layer raises ValueError
    try:
        item = approve_item(db, item_id, body.reviewed_by)
    except ValueError as exc:
        _raise_conflict(exc)
    logger.info(
        "[routes] approve_queue_item: approved item id=%d by %s",
        item_id,
        body.reviewed_by,
    )
    return item


@router.post(
    "/queue/{item_id}/reject",
    response_model=QueueItemResponse,
    summary="Reject a pending queue item",
    tags=["Approval Queue"],
)
def reject_queue_item(
    item_id: int,
    body: QueueActionRequest,
    db: Session = Depends(get_db),
) -> ApprovalQueue:
    """Mark a pending queue item as rejected.

    The item must currently have status='pending'. After rejection it moves to
    status='rejected' and will not be executed.

    Args:
        item_id: Primary key of the ApprovalQueue row to reject.
        body: Must contain reviewed_by (email or username of the reviewer).

    Returns:
        Updated QueueItemResponse with status='rejected'.

    Raises:
        HTTPException: 404 if the item does not exist.
        HTTPException: 409 if the item is not currently pending.
    """
    _get_queue_item_or_404(item_id, db)  # raises 404 before queue layer raises ValueError
    try:
        item = reject_item(db, item_id, body.reviewed_by)
    except ValueError as exc:
        _raise_conflict(exc)
    logger.info(
        "[routes] reject_queue_item: rejected item id=%d by %s",
        item_id,
        body.reviewed_by,
    )
    return item


@router.post(
    "/queue/{item_id}/execute",
    response_model=QueueItemResponse,
    summary="Execute an approved queue item via the Google Ads API",
    tags=["Approval Queue"],
)
def execute_queue_item(
    item_id: int,
    db: Session = Depends(get_db),
    ads_client: AdsClient = Depends(_get_ads_client),
) -> ApprovalQueue:
    """Execute an approved queue item against the Google Ads API.

    The item must have status='approved'. After successful execution it moves
    to status='executed'. On API failure it moves to status='failed' and the
    failure_reason field is populated.

    Args:
        item_id: Primary key of the ApprovalQueue row to execute.

    Returns:
        Updated QueueItemResponse reflecting the post-execution status.

    Raises:
        HTTPException: 404 if the item does not exist.
        HTTPException: 409 if the item is not in status='approved'.
        HTTPException: 502 on Google Ads API execution failure.
    """
    item = _get_queue_item_or_404(item_id, db)

    if item.status != "approved":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Queue item id={item_id} cannot be executed — "
                f"current status is '{item.status}' (must be 'approved')"
            ),
        )

    # Resolve customer_id from the linked account
    account = _get_account_or_404(item.account_id, db)
    customer_id = account.customer_id

    executor = Executor(ads_client, db)
    try:
        executor.execute_approved(item, customer_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(
            "[routes] execute_queue_item: execution failed for item id=%d",
            item_id,
        )
        raise HTTPException(
            status_code=502,
            detail=f"Google Ads API execution failed: {exc}",
        ) from exc

    db.refresh(item)
    logger.info(
        "[routes] execute_queue_item: executed item id=%d for account id=%d",
        item_id,
        item.account_id,
    )
    return item


# ── Campaign creation route ────────────────────────────────────────────────────

@router.post(
    "/campaigns/create",
    response_model=CreateCampaignResponse,
    status_code=201,
    summary="Trigger the Creator agent to generate a campaign from a brief",
    tags=["Campaigns"],
)
def create_campaign(
    body: CampaignBriefRequest,
    db: Session = Depends(get_db),
    ads_client: AdsClient = Depends(_get_ads_client),
    claude_client: ClaudeClient = Depends(_get_claude_client),
) -> CreateCampaignResponse:
    """Generate a full campaign structure from a human-authored brief.

    The Creator agent calls Claude with the brief and the account's context,
    then writes the resulting structure to the approval queue as a single
    create_campaign action. No Google Ads API call is made here — a human must
    approve the queue item first.

    Args:
        body: CampaignBriefRequest containing account_id and the brief dict.

    Returns:
        CreateCampaignResponse with the queue item ID, status, and the full
        campaign structure generated by Claude.

    Raises:
        HTTPException: 404 if the account does not exist.
        HTTPException: 422 if Claude returns an invalid campaign structure.
        HTTPException: 502 if the Claude API call fails.
    """
    account = _get_account_or_404(body.account_id, db)

    creator = CreatorAgent(
        ads_client=ads_client,
        claude_client=claude_client,
        db_session=db,
    )

    try:
        queue_item, campaign_structure = creator.create_from_brief(
            account=account,
            brief=body.brief.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(
            "[routes] create_campaign: Creator agent failed for account id=%d",
            body.account_id,
        )
        raise HTTPException(
            status_code=502,
            detail=f"Campaign generation failed: {exc}",
        ) from exc

    logger.info(
        "[routes] create_campaign: queued item id=%d for account id=%d",
        queue_item.id,
        body.account_id,
    )

    return CreateCampaignResponse(
        queue_item_id=queue_item.id,
        status=queue_item.status,
        campaign_structure=campaign_structure,
    )


# ── Audit log route ────────────────────────────────────────────────────────────

@router.get(
    "/audit",
    response_model=list[AuditLogResponse],
    summary="List recent audit log entries",
    tags=["Audit"],
)
def list_audit_log(
    account_id: int | None = Query(None, description="Filter by account ID"),
    severity: str | None = Query(None, description="Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of entries to return"),
    db: Session = Depends(get_db),
) -> list[AuditLog]:
    """Return recent audit log entries, newest first.

    Args:
        account_id: When supplied, only entries for this account are returned.
        severity: When supplied, only entries with this severity are returned.
        limit: Maximum number of rows to return (default 100, max 1000).

    Returns:
        List of AuditLogResponse objects ordered by run_time descending.
    """
    stmt = select(AuditLog)

    if account_id is not None:
        stmt = stmt.where(AuditLog.account_id == account_id)
    if severity is not None:
        stmt = stmt.where(AuditLog.severity == severity.upper())

    stmt = stmt.order_by(AuditLog.run_time.desc()).limit(limit)

    entries = list(db.scalars(stmt).all())
    logger.debug(
        "[routes] list_audit_log: returning %d entries (account_id=%s, severity=%s)",
        len(entries),
        account_id,
        severity,
    )
    return entries


# ── Internal helpers ───────────────────────────────────────────────────────────

def _raise_conflict(exc: ValueError) -> None:
    """Convert a ValueError from the queue layer into an HTTP 409 response.

    Args:
        exc: ValueError raised by approve_item() or reject_item().

    Raises:
        HTTPException: Always — 409 Conflict with the exception message.
    """
    raise HTTPException(status_code=409, detail=str(exc)) from exc
