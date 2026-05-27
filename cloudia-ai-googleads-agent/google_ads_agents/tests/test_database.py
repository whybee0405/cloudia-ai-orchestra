"""Section 2 — Database integrity tests."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.models import Account, AgentRun, ApprovalQueue, AuditLog, CampaignSnapshot, IndustryBenchmark
from db.queue import approve_item, reject_item, write_queue_item
from tests.factories import make_account


# ── 2.1 Schema Tests ───────────────────────────────────────────────────────────

def test_all_tables_create(db_session: Session) -> None:
    """All six tables exist and are queryable."""
    for model in [Account, CampaignSnapshot, AuditLog, ApprovalQueue, IndustryBenchmark, AgentRun]:
        result = db_session.query(model).all()
        assert isinstance(result, list)


def test_campaign_snapshot_foreign_key_enforced(db_session: Session) -> None:
    """Inserting a snapshot with a non-existent account_id must fail."""
    from datetime import datetime, timezone

    snap = CampaignSnapshot(
        account_id=99999,  # does not exist
        campaign_id="aaa",
        snapshot_time=datetime.now(timezone.utc),
    )
    db_session.add(snap)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_approval_queue_foreign_key_enforced(db_session: Session) -> None:
    """Inserting a queue item with a non-existent account_id must fail."""
    item = ApprovalQueue(
        account_id=99999,
        agent_name="manager",
        action_type="increase_bid",
        status="pending",
    )
    db_session.add(item)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_account_not_null_constraints(db_session: Session) -> None:
    """Inserting an Account without required fields must fail."""
    account = Account(
        # client_name is NOT NULL
        customer_id="abc",
        mcc_id="def",
    )
    db_session.add(account)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_jsonb_fields_accept_valid_json(db_session: Session) -> None:
    """JSONB/JSON columns accept valid Python dicts."""
    data = make_account()
    account = Account(**data)
    db_session.add(account)
    db_session.flush()
    db_session.refresh(account)

    assert account.custom_rules == data["custom_rules"]
    assert account.peak_months == data["peak_months"]


# ── 2.2 Data Integrity Tests ───────────────────────────────────────────────────

def test_customer_id_unique_constraint(db_session: Session) -> None:
    """Two accounts cannot share the same customer_id."""
    data = make_account({"customer_id": "UNIQUE-123"})
    a1 = Account(**data)
    a2 = Account(**{**data, "client_name": "Different Name"})

    db_session.add(a1)
    db_session.flush()
    db_session.add(a2)
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()


def test_cascade_delete_clears_snapshots(db_session: Session) -> None:
    """Deleting an account must cascade-delete its campaign_snapshots."""
    from datetime import datetime, timezone

    account = Account(**make_account({"customer_id": "CASCADE-TEST"}))
    db_session.add(account)
    db_session.flush()

    snap = CampaignSnapshot(
        account_id=account.id,
        campaign_id="cam1",
        snapshot_time=datetime.now(timezone.utc),
    )
    db_session.add(snap)
    db_session.flush()

    snap_id = snap.id
    db_session.delete(account)
    db_session.flush()

    deleted = db_session.query(CampaignSnapshot).filter_by(id=snap_id).first()
    assert deleted is None


def test_cascade_delete_clears_queue_items(db_session: Session) -> None:
    """Deleting an account must cascade-delete its approval_queue rows."""
    account = Account(**make_account({"customer_id": "CASCADE-QUEUE"}))
    db_session.add(account)
    db_session.flush()

    item = ApprovalQueue(
        account_id=account.id,
        agent_name="manager",
        action_type="increase_bid",
        status="pending",
    )
    db_session.add(item)
    db_session.flush()

    item_id = item.id
    db_session.delete(account)
    db_session.flush()

    deleted = db_session.query(ApprovalQueue).filter_by(id=item_id).first()
    assert deleted is None


def test_queue_status_pending_to_approved(db_session: Session) -> None:
    """pending → approved transition is valid."""
    account = Account(**make_account({"customer_id": "STATUS-TEST-1"}))
    db_session.add(account)
    db_session.flush()

    item = write_queue_item(
        db=db_session,
        account_id=account.id,
        agent_name="manager",
        action_type="increase_bid",
        action_payload={},
        reasoning="test",
    )
    approved = approve_item(db_session, item.id, "tester@example.com")
    assert approved.status == "approved"


def test_queue_status_pending_to_rejected(db_session: Session) -> None:
    """pending → rejected transition is valid."""
    account = Account(**make_account({"customer_id": "STATUS-TEST-2"}))
    db_session.add(account)
    db_session.flush()

    item = write_queue_item(
        db=db_session,
        account_id=account.id,
        agent_name="manager",
        action_type="increase_bid",
        action_payload={},
        reasoning="test",
    )
    rejected = reject_item(db_session, item.id, "tester@example.com")
    assert rejected.status == "rejected"


def test_cannot_approve_already_executed_item(db_session: Session) -> None:
    """Approving an already-executed item must raise ValueError."""
    account = Account(**make_account({"customer_id": "STATUS-TEST-3"}))
    db_session.add(account)
    db_session.flush()

    item = write_queue_item(
        db=db_session,
        account_id=account.id,
        agent_name="manager",
        action_type="increase_bid",
        action_payload={},
        reasoning="test",
    )
    item.status = "executed"
    db_session.flush()

    with pytest.raises(ValueError, match="cannot be approved"):
        approve_item(db_session, item.id, "tester@example.com")
