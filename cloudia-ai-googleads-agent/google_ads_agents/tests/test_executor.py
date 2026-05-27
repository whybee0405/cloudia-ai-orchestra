"""Section 9 — Executor stress tests + legacy queue tests."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from db.models import ApprovalQueue
from db.queue import approve_item, reject_item, write_queue_item
from google_ads.executor import AlreadyExecutedError, Executor, SecurityError


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_item(status: str = "approved") -> ApprovalQueue:
    item = ApprovalQueue(
        id=1,
        account_id=1,
        agent_name="manager",
        action_type="increase_bid",
        action_payload={"ad_group_id": "ag1", "new_value_micros": 20_000_000},
        reasoning="CTR above baseline",
        status=status,
    )
    return item


def _make_pending_item(item_id: int = 1) -> ApprovalQueue:
    return ApprovalQueue(
        id=item_id, account_id=1, agent_name="manager", action_type="increase_bid",
        action_payload={"target_id": "ag_1", "recommended_value": 200_000},
        reasoning="Bid increase recommended", status="pending",
    )


# ── 9.1 Executor permission checks ────────────────────────────────────────────

def test_executor_raises_permission_error_for_pending_item(mock_ads_client, mock_db_session):
    item = _make_item(status="pending")
    executor = Executor(mock_ads_client, mock_db_session)
    with pytest.raises(PermissionError):
        executor.execute_approved(item, "123")


def test_executor_raises_permission_error_for_rejected_item(mock_ads_client, mock_db_session):
    item = _make_item(status="rejected")
    executor = Executor(mock_ads_client, mock_db_session)
    with pytest.raises(PermissionError):
        executor.execute_approved(item, "123")


def test_executor_raises_already_executed_error(mock_ads_client, mock_db_session):
    item = _make_item(status="executed")
    item.executed_at = datetime.now(timezone.utc)
    executor = Executor(mock_ads_client, mock_db_session)
    with pytest.raises(AlreadyExecutedError):
        executor.execute_approved(item, "123")


def test_executor_raises_value_error_for_unknown_action(mock_ads_client, mock_db_session):
    item = _make_item(status="approved")
    item.action_type = "delete_account"
    executor = Executor(mock_ads_client, mock_db_session)
    with pytest.raises(ValueError, match="Unknown action_type"):
        executor.execute_approved(item, "123")


def test_executor_sets_status_executed_on_success(mock_ads_client, mock_db_session):
    """Successful execution sets status to 'executed' and records executed_at."""
    item = _make_item(status="approved")
    mock_db_session.commit.return_value = None

    executor = Executor(mock_ads_client, mock_db_session)

    with patch.object(executor, "_set_ad_group_bid", return_value={"resource_name": "res/1"}):
        executor.execute_approved(item, "123")

    assert item.status == "executed"
    assert item.executed_at is not None


def test_executor_sets_status_failed_on_google_ads_exception(mock_ads_client, mock_db_session):
    """GoogleAdsException sets status='failed' and writes failure_reason."""
    from google.ads.googleads.errors import GoogleAdsException

    item = _make_item(status="approved")
    mock_db_session.commit.return_value = None

    executor = Executor(mock_ads_client, mock_db_session)

    # Build a realistic GoogleAdsException mock
    error = MagicMock()
    error.message = "POLICY_VIOLATION: ad content not permitted"
    error.error_code.ListFields.return_value = []
    failure = MagicMock()
    failure.errors = [error]
    exc = GoogleAdsException(None, None, failure, None)

    with patch.object(executor, "_set_ad_group_bid", side_effect=exc):
        with pytest.raises(GoogleAdsException):
            executor.execute_approved(item, "123")

    assert item.status == "failed"
    assert item.failure_reason is not None


# ── Legacy queue tests (preserved) ────────────────────────────────────────────

def test_write_queue_item_sets_pending(mock_db_session: MagicMock) -> None:
    def _fake_refresh(obj: ApprovalQueue) -> None:
        obj.id = 42

    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.side_effect = _fake_refresh

    item = write_queue_item(
        db=mock_db_session, account_id=1, agent_name="manager",
        action_type="increase_bid", action_payload={"target_id": "ag_1"}, reasoning="Bid is too low",
    )
    assert item.status == "pending"
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()


def test_approve_item_raises_if_not_pending(mock_db_session: MagicMock) -> None:
    executed_item = _make_pending_item(item_id=7)
    executed_item.status = "executed"
    with patch("db.queue.get_item_by_id", return_value=executed_item):
        with pytest.raises(ValueError, match="cannot be approved"):
            approve_item(db=mock_db_session, item_id=7, reviewed_by="user@example.com")


def test_reject_item_sets_rejected(mock_db_session: MagicMock) -> None:
    pending_item = _make_pending_item(item_id=5)
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None
    with patch("db.queue.get_item_by_id", return_value=pending_item):
        result = reject_item(db=mock_db_session, item_id=5, reviewed_by="reviewer@example.com")
    assert result.status == "rejected"
    assert result.reviewed_by == "reviewer@example.com"
    mock_db_session.commit.assert_called_once()
