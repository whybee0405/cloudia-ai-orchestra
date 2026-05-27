"""Section 12 — Integration tests. End-to-end flows using the real SQLite DB."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from agents.auditor import AuditorAgent
from agents.manager import ManagerAgent
from db.models import Account, ApprovalQueue, AuditLog, CampaignSnapshot
from db.queue import approve_item, write_queue_item
from tests.factories import make_account, make_benchmarks


# ── 12.1 Full Auditor Cycle ────────────────────────────────────────────────────

def test_full_auditor_cycle(db_session, mock_ads_client, mock_claude_client):
    """Full auditor run: snapshot stored, anomaly written, Claude called with context."""
    account = Account(**make_account({"customer_id": "INT-AUD-001"}))
    db_session.add(account)
    db_session.flush()

    # Create a previous snapshot so the auditor can diff
    prev_snap = CampaignSnapshot(
        account_id=account.id,
        campaign_id="cam1",
        campaign_name="Brand Campaign",
        snapshot_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        impressions=5000, clicks=225, cost_micros=4_500_000_000,
        conversions=7.0, ctr=0.10, avg_cpc_micros=20_000_000,
        conversion_rate=0.031, cost_per_conversion=642_857_143,
    )
    db_session.add(prev_snap)
    db_session.flush()

    # Mock current campaign data with severe CTR drop
    current_snap_data = {
        "campaign_id": "cam1", "campaign_name": "Brand Campaign", "status": "ENABLED",
        "impressions": 5000, "clicks": 100, "cost_micros": 4_500_000_000,
        "conversions": 7.0, "ctr": 0.02,  # -80% CTR drop
        "avg_cpc_micros": 20_000_000, "conversion_rate": 0.07,
        "cost_per_conversion": None, "budget_micros": 500_000_000,
    }

    mock_ads_client.run_query.return_value = ["fake_row"]
    mock_claude_client.complete_json.return_value = ({
        "anomaly_type": "ctr_drop", "severity": "HIGH",
        "diagnosis": "CTR dropped 80% vs prior period.",
        "recommended_action": "Review ad copy immediately.",
    }, 300)

    agent = AuditorAgent(mock_ads_client, mock_claude_client, db_session)

    with patch("agents.auditor.parse_gaql_row", return_value=current_snap_data), \
         patch("agents.auditor.send_alert") as mock_alert:
        result = agent.execute(account)

    # Snapshot was stored
    snaps = db_session.query(CampaignSnapshot).filter_by(account_id=account.id).all()
    assert len(snaps) >= 2

    # Audit log entry was created
    audit_entries = db_session.query(AuditLog).filter_by(account_id=account.id).all()
    assert len(audit_entries) >= 1

    # HIGH severity triggers email alert
    mock_alert.assert_called_once()

    # Claude was called
    mock_claude_client.complete_json.assert_called()
    call_args = mock_claude_client.complete_json.call_args[1]
    assert account.client_name in call_args.get("user_message", "") or \
           account.client_name in str(call_args)


# ── 12.2 Full Manager Cycle ────────────────────────────────────────────────────

def test_full_manager_cycle_rule_violation_not_queued(db_session, mock_ads_client, mock_claude_client):
    """Manager: rule-violating decision excluded, valid decision queued, approves successfully."""
    account = Account(**make_account({
        "customer_id": "INT-MGR-001",
        "custom_rules": {
            "never_pause_brand_campaign": True,
            "max_cpc_increase_pct": 15,
        },
    }))
    db_session.add(account)
    db_session.flush()

    # Claude returns: one valid decision + one rule-violating decision
    mock_ads_client.run_query.return_value = [MagicMock()]
    mock_claude_client.complete_json.return_value = ({
        "decisions": [
            {
                "action_type": "increase_bid",
                "target_id": "ag1",
                "target_name": "Brand Ad Group",
                "current_value": 15_000_000,
                "recommended_value": 17_000_000,  # +13.3% — within 15% limit
                "reasoning": "CTR above baseline",
            },
            {
                "action_type": "pause_campaign",  # blocked by never_pause_brand_campaign
                "target_id": "cmp1",
                "target_name": "Brand Campaign",
                "current_value": None,
                "recommended_value": None,
                "reasoning": "Low volume",
            },
        ]
    }, 400)

    agent = ManagerAgent(mock_ads_client, mock_claude_client, db_session)

    with patch("agents.manager.build_client_context", return_value="ctx"), \
         patch("agents.manager.send_queue_summary"), \
         patch("agents.manager._parse_adgroup_row", return_value={"adgroup_id": "ag1",
               "adgroup_name": "Brand", "adgroup_status": "ENABLED", "cpc_bid_micros": 0,
               "campaign_id": "cmp1", "campaign_name": "Brand", "impressions": 100,
               "clicks": 5, "ctr": 0.05, "conversions": 1.0, "avg_cpc_micros": 0}), \
         patch("agents.manager._parse_campaign_row", return_value={"campaign_id": "cmp1",
               "campaign_name": "Brand", "status": "ENABLED", "budget_micros": 200_000_000,
               "impressions": 100, "clicks": 5, "cost_micros": 0, "conversions": 1.0,
               "ctr": 0.05, "avg_cpc_micros": 0, "cost_per_conversion": 0,
               "conversion_rate": 0.2, "search_impression_share": 0.5}):
        result = agent.execute(account)

    # Only 1 decision should have been queued (pause was blocked)
    queue_items = db_session.query(ApprovalQueue).filter_by(account_id=account.id).all()
    assert len(queue_items) == 1
    assert queue_items[0].action_type == "increase_bid"
    assert queue_items[0].status == "pending"

    # Approve it and verify status change
    approved = approve_item(db_session, queue_items[0].id, "manager@cloudia.co.za")
    assert approved.status == "approved"


# ── 12.3 Multi-Client Isolation ────────────────────────────────────────────────

def test_multi_client_data_isolation(db_session, mock_ads_client, mock_claude_client):
    """Two accounts' snapshots and queue items must never cross-contaminate."""
    account_a = Account(**make_account({"customer_id": "ISO-A001", "client_name": "Client A"}))
    account_b = Account(**make_account({"customer_id": "ISO-B002", "client_name": "Client B"}))
    db_session.add_all([account_a, account_b])
    db_session.flush()

    # Write queue items for each account
    item_a = write_queue_item(db_session, account_a.id, "manager", "increase_bid",
                               {"target": "a"}, "reason a")
    item_b = write_queue_item(db_session, account_b.id, "manager", "increase_bid",
                               {"target": "b"}, "reason b")

    # Verify isolation: only A's items returned when filtering by A's account_id
    from db.queue import get_pending_items
    a_items = get_pending_items(db_session, account_id=account_a.id)
    b_items = get_pending_items(db_session, account_id=account_b.id)

    assert all(i.account_id == account_a.id for i in a_items)
    assert all(i.account_id == account_b.id for i in b_items)
    assert item_a.id not in {i.id for i in b_items}
    assert item_b.id not in {i.id for i in a_items}
