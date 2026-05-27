"""Section 13 — Performance tests (timing assertions)."""

import time
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from ai.context_builder import build_client_context
from db.models import Account, CampaignSnapshot, IndustryBenchmark
from tests.factories import make_account, make_benchmarks, make_snapshot


def _full_account() -> Account:
    return Account(**make_account({
        "customer_id": "PERF-001",
        "custom_rules": {
            "never_pause_brand_campaign": True,
            "max_cpc_increase_pct": 15,
            "competitor_bidding_allowed": False,
            "max_daily_spend_increase_pct": 20,
        },
    }))


def test_context_builder_under_5ms():
    """context_builder with full account data must run under 5ms."""
    account = _full_account()
    benchmarks = IndustryBenchmark(**make_benchmarks())

    start = time.perf_counter()
    for _ in range(100):
        build_client_context(account, benchmarks)
    elapsed_ms = (time.perf_counter() - start) * 1000 / 100

    assert elapsed_ms < 5, f"context_builder took {elapsed_ms:.2f}ms (limit: 5ms)"


def test_queue_get_pending_with_many_items_under_500ms(db_session):
    """GET /queue with 100 pending items in DB must complete under 500ms."""
    from tests.factories import make_account
    from db.models import Account as Acc, ApprovalQueue

    account = Acc(**make_account({"customer_id": "PERF-QUEUE-001"}))
    db_session.add(account)
    db_session.flush()

    items = [
        ApprovalQueue(account_id=account.id, agent_name="manager",
                      action_type="increase_bid", status="pending")
        for _ in range(100)
    ]
    db_session.bulk_save_objects(items)
    db_session.flush()

    start = time.perf_counter()
    from db.queue import get_pending_items
    results = get_pending_items(db_session, account_id=account.id)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 500, f"get_pending_items took {elapsed_ms:.2f}ms (limit: 500ms)"
    assert len(results) == 100


def test_snapshot_query_performance_under_1s(db_session):
    """DB query for campaign_snapshots must complete under 1s for 90 days of data."""
    from db.models import Account as Acc
    from tests.factories import make_account
    from datetime import timedelta

    account = Acc(**make_account({"customer_id": "PERF-SNAP-001"}))
    db_session.add(account)
    db_session.flush()

    now = datetime.now(timezone.utc)
    snaps = [
        CampaignSnapshot(
            account_id=account.id,
            campaign_id=f"cam{i % 5}",
            snapshot_time=now - timedelta(days=i),
            impressions=1000, clicks=45, cost_micros=900_000_000,
        )
        for i in range(90)
    ]
    db_session.bulk_save_objects(snaps)
    db_session.flush()

    start = time.perf_counter()
    from sqlalchemy import select
    stmt = select(CampaignSnapshot).where(CampaignSnapshot.account_id == account.id)
    results = list(db_session.scalars(stmt).all())
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 1000, f"snapshot query took {elapsed_ms:.2f}ms (limit: 1000ms)"
    assert len(results) == 90


def test_context_builder_output_under_2000_tokens():
    """Full context builder output must not exceed ~2000 tokens (estimate: 4 chars/token)."""
    account = _full_account()
    account.notes = "A" * 500  # notes aren't in the context so this is a control
    benchmarks = IndustryBenchmark(**make_benchmarks())
    ctx = build_client_context(account, benchmarks)

    # Rough token estimate: 4 chars per token
    estimated_tokens = len(ctx) / 4
    assert estimated_tokens < 2000, f"Context estimated at {estimated_tokens:.0f} tokens (limit: 2000)"
