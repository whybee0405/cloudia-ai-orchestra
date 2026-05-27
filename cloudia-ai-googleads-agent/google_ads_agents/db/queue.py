"""Approval queue read/write logic.

All agent decisions pass through this module before any action is taken.
Nothing in the system executes against the Google Ads API without a human
first approving the relevant ApprovalQueue row via the dashboard.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

import config
from db.models import ApprovalQueue

logger = logging.getLogger(__name__)


def write_queue_item(
    db: Session,
    account_id: int,
    agent_name: str,
    action_type: str,
    action_payload: dict,
    reasoning: str,
) -> ApprovalQueue:
    """Create and commit a new ApprovalQueue row with status='pending'.

    Args:
        db: Active SQLAlchemy session.
        account_id: The account this decision belongs to.
        agent_name: Name of the agent that generated the decision
                    (e.g. 'manager', 'keyword_scout').
        action_type: Machine-readable action identifier
                     (e.g. 'increase_bid', 'pause_campaign').
        action_payload: Full decision payload as a dict — stored as JSONB.
                        Should contain at minimum target_id, target_name,
                        current_value, and recommended_value.
        reasoning: Human-readable explanation from Claude of why this action
                   is recommended.

    Returns:
        The newly created and committed ApprovalQueue ORM row.
    """
    item = ApprovalQueue(
        account_id=account_id,
        agent_name=agent_name,
        action_type=action_type,
        action_payload=action_payload,
        reasoning=reasoning,
        status=config.QUEUE_STATUS_PENDING,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    logger.info(
        "[queue] Created pending item id=%d  account=%d  agent=%s  action=%s",
        item.id,
        account_id,
        agent_name,
        action_type,
    )
    return item


def get_pending_items(
    db: Session,
    account_id: int | None = None,
) -> list[ApprovalQueue]:
    """Return all pending approval queue items, newest first.

    Args:
        db: Active SQLAlchemy session.
        account_id: When provided, filter results to this account only.
                    When None, return pending items across all accounts.

    Returns:
        List of ApprovalQueue rows with status='pending', ordered by
        created_at descending.
    """
    stmt = select(ApprovalQueue).where(
        ApprovalQueue.status == config.QUEUE_STATUS_PENDING
    )

    if account_id is not None:
        stmt = stmt.where(ApprovalQueue.account_id == account_id)

    stmt = stmt.order_by(ApprovalQueue.created_at.desc())

    items = list(db.scalars(stmt).all())
    logger.debug(
        "[queue] get_pending_items: found %d items (account_id=%s)",
        len(items),
        account_id,
    )
    return items


def approve_item(
    db: Session,
    item_id: int,
    reviewed_by: str,
) -> ApprovalQueue:
    """Mark an approval queue item as approved.

    Sets status='approved', reviewed_at=now(UTC), and reviewed_by to the
    supplied identifier (typically an email address or username).

    Args:
        db: Active SQLAlchemy session.
        item_id: Primary key of the ApprovalQueue row to approve.
        reviewed_by: Identifier of the human reviewer (email or username).

    Returns:
        The updated ApprovalQueue row.

    Raises:
        ValueError: If the item is not found, or is not currently pending
                    (i.e. already approved, rejected, or executed).
    """
    item = get_item_by_id(db, item_id)

    if item is None:
        raise ValueError(f"ApprovalQueue item id={item_id} not found")

    if item.status != config.QUEUE_STATUS_PENDING:
        raise ValueError(
            f"ApprovalQueue item id={item_id} cannot be approved — "
            f"current status is '{item.status}' (must be 'pending')"
        )

    item.status = config.QUEUE_STATUS_APPROVED
    item.reviewed_at = datetime.now(timezone.utc)
    item.reviewed_by = reviewed_by
    db.commit()
    db.refresh(item)

    logger.info(
        "[queue] Approved item id=%d  account=%d  action=%s  reviewed_by=%s",
        item.id,
        item.account_id,
        item.action_type,
        reviewed_by,
    )
    return item


def reject_item(
    db: Session,
    item_id: int,
    reviewed_by: str,
) -> ApprovalQueue:
    """Mark an approval queue item as rejected.

    Sets status='rejected', reviewed_at=now(UTC), and reviewed_by to the
    supplied identifier (typically an email address or username).

    Args:
        db: Active SQLAlchemy session.
        item_id: Primary key of the ApprovalQueue row to reject.
        reviewed_by: Identifier of the human reviewer (email or username).

    Returns:
        The updated ApprovalQueue row.

    Raises:
        ValueError: If the item is not found, or is not currently pending
                    (i.e. already approved, rejected, or executed).
    """
    item = get_item_by_id(db, item_id)

    if item is None:
        raise ValueError(f"ApprovalQueue item id={item_id} not found")

    if item.status != config.QUEUE_STATUS_PENDING:
        raise ValueError(
            f"ApprovalQueue item id={item_id} cannot be rejected — "
            f"current status is '{item.status}' (must be 'pending')"
        )

    item.status = config.QUEUE_STATUS_REJECTED
    item.reviewed_at = datetime.now(timezone.utc)
    item.reviewed_by = reviewed_by
    db.commit()
    db.refresh(item)

    logger.info(
        "[queue] Rejected item id=%d  account=%d  action=%s  reviewed_by=%s",
        item.id,
        item.account_id,
        item.action_type,
        reviewed_by,
    )
    return item


def get_item_by_id(
    db: Session,
    item_id: int,
) -> ApprovalQueue | None:
    """Return a single ApprovalQueue row by primary key, or None.

    Args:
        db: Active SQLAlchemy session.
        item_id: Primary key of the row to fetch.

    Returns:
        The matching ApprovalQueue row, or None if not found.
    """
    stmt = select(ApprovalQueue).where(ApprovalQueue.id == item_id)
    item = db.scalars(stmt).first()

    if item is None:
        logger.debug("[queue] get_item_by_id: id=%d not found", item_id)
    return item
