"""Section 5 — Manager stress tests (custom rules, payload validation, queue integrity)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from agents.manager import ManagerAgent, _check_custom_rules, _validate_decision_payload
from agents.base import AgentRunResult
from db.models import Account


def _make_account(**overrides) -> Account:
    defaults: dict = dict(
        id=1, client_name="Test Motors", customer_id="1234567890", mcc_id="0987654321",
        status="active", industry="automotive_parts", business_type="local_service",
        avg_transaction_value=2500.00, primary_kpi="CPL", primary_kpi_target=450.00,
        monthly_ad_spend=15000.00, budget_sensitivity="moderate", min_daily_budget=200.00,
        baseline_ctr=0.045, baseline_cvr=0.032, baseline_cpc=18.50, baseline_cpa=420.00,
        baseline_roas=3.20, baseline_set_at=datetime(2025, 1, 1),
        peak_months=[10, 11, 12], slow_months=[6, 7],
        custom_rules={"never_pause_brand_campaign": True, "max_cpc_increase_pct": 15},
        alert_email="alerts@test.co.za", report_email="reports@test.co.za",
    )
    defaults.update(overrides)
    return Account(**defaults)


def _make_campaign_row() -> MagicMock:
    row = MagicMock()
    row.campaign.id = 111
    row.campaign.name = "Test Campaign"
    row.campaign.status.name = "ENABLED"
    row.campaign_budget.amount_micros = 200_000_000
    row.metrics.impressions = 10_000
    row.metrics.clicks = 400
    row.metrics.cost_micros = 74_000_000
    row.metrics.conversions = 20
    row.metrics.ctr = 0.04
    row.metrics.average_cpc = 185_000
    row.metrics.cost_per_conversion = 3_700_000
    row.metrics.conversions_from_interactions_rate = 0.05
    row.metrics.search_impression_share = 0.60
    return row


# ── 5.1 Custom Rules Enforcement ───────────────────────────────────────────────

def test_never_pause_brand_blocks_pause():
    decision = {"action_type": "pause_campaign", "reasoning": "test"}
    result = _check_custom_rules(decision, {"never_pause_brand_campaign": True})
    assert result == "never_pause_brand_campaign"


def test_max_cpc_increase_16pct_blocked():
    decision = {"action_type": "increase_bid", "current_value": 100, "recommended_value": 116}
    result = _check_custom_rules(decision, {"max_cpc_increase_pct": 15})
    assert result == "max_cpc_increase_pct"


def test_max_cpc_increase_15pct_allowed():
    decision = {"action_type": "increase_bid", "current_value": 100, "recommended_value": 115}
    assert _check_custom_rules(decision, {"max_cpc_increase_pct": 15}) is None


def test_max_cpc_increase_14pct_allowed():
    decision = {"action_type": "increase_bid", "current_value": 100, "recommended_value": 114}
    assert _check_custom_rules(decision, {"max_cpc_increase_pct": 15}) is None


def test_competitor_keyword_blocked_when_not_allowed():
    decision = {"action_type": "add_keyword", "is_competitor_keyword": True, "reasoning": "bid on competitor"}
    result = _check_custom_rules(decision, {"competitor_bidding_allowed": False})
    assert result == "competitor_bidding_allowed"


def test_competitor_keyword_allowed_when_permitted():
    decision = {"action_type": "add_keyword", "is_competitor_keyword": True, "reasoning": "bid on competitor"}
    assert _check_custom_rules(decision, {"competitor_bidding_allowed": True}) is None


def test_max_daily_spend_11pct_blocked():
    decision = {"action_type": "increase_budget", "current_value": 100, "recommended_value": 111}
    result = _check_custom_rules(decision, {"max_daily_spend_increase_pct": 10})
    assert result == "max_daily_spend_increase_pct"


def test_no_custom_rules_all_pass():
    decision = {"action_type": "pause_campaign", "reasoning": "test"}
    assert _check_custom_rules(decision, {}) is None


# ── 5.2 Decision Payload Validation ───────────────────────────────────────────

def test_unknown_action_type_rejected():
    decision = {"action_type": "delete_account"}
    result = _validate_decision_payload(decision)
    assert result is not None and "unknown_action_type" in result


def test_increase_bid_lower_than_current_rejected():
    decision = {"action_type": "increase_bid", "current_value": 20_000_000, "recommended_value": 15_000_000}
    result = _validate_decision_payload(decision)
    assert result == "increase_bid_not_higher_than_current"


def test_increase_budget_to_zero_rejected():
    decision = {"action_type": "increase_budget", "current_value": 200_000_000, "recommended_value": 0}
    result = _validate_decision_payload(decision)
    assert result is not None


def test_pause_campaign_missing_reasoning_rejected():
    decision = {"action_type": "pause_campaign"}
    result = _validate_decision_payload(decision)
    assert result == "pause_campaign_missing_reasoning"


def test_valid_increase_bid_passes_validation():
    decision = {"action_type": "increase_bid", "current_value": 100, "recommended_value": 110, "reasoning": "good"}
    assert _validate_decision_payload(decision) is None


def test_valid_pause_campaign_passes_validation():
    decision = {"action_type": "pause_campaign", "reasoning": "CTR below threshold for 14 days"}
    assert _validate_decision_payload(decision) is None


# ── Legacy tests ────────────────────────────────────────────────────────────────

def test_manager_skips_calibrating(mock_ads_client, mock_claude_client, mock_db_session):
    account = _make_account(baseline_set_at=None)
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    agent = ManagerAgent(mock_ads_client, mock_claude_client, mock_db_session)
    result = agent.run(account)
    assert result.status == "skipped"
    mock_ads_client.run_query.assert_not_called()


def test_manager_no_decisions(mock_ads_client, mock_claude_client, mock_db_session, sample_account):
    mock_ads_client.run_query.side_effect = [[_make_campaign_row()], []]
    mock_claude_client.complete_json.return_value = ({"decisions": []}, 50)
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    agent = ManagerAgent(mock_ads_client, mock_claude_client, mock_db_session)
    with patch("agents.manager.build_client_context", return_value="ctx"), \
         patch("agents.manager.send_queue_summary"):
        result = agent.run(sample_account)
    assert result.status == "success"
    assert result.decisions_generated == 0


def test_manager_writes_queue_items(mock_ads_client, mock_claude_client, mock_db_session, sample_account):
    mock_ads_client.run_query.side_effect = [[_make_campaign_row()], []]
    two_decisions = {
        "decisions": [
            {"action_type": "increase_bid", "target_id": "ag1", "target_name": "AdGroup Alpha",
             "current_value": 185_000, "recommended_value": 200_000, "reasoning": "CTR above baseline"},
            {"action_type": "increase_budget", "target_id": "cmp111", "target_name": "Test Campaign",
             "current_value": 200_000_000, "recommended_value": 220_000_000, "reasoning": "Low impression share"},
        ]
    }
    mock_claude_client.complete_json.return_value = (two_decisions, 120)
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None
    agent = ManagerAgent(mock_ads_client, mock_claude_client, mock_db_session)
    with patch("agents.manager.build_client_context", return_value="ctx"), \
         patch("agents.manager.send_queue_summary"), \
         patch("agents.manager.write_queue_item") as mock_write:
        result = agent.run(sample_account)
    assert mock_write.call_count == 2
    assert result.decisions_generated == 2


def test_manager_respects_never_pause_brand_rule(mock_ads_client, mock_claude_client, mock_db_session):
    account = _make_account(custom_rules={"never_pause_brand_campaign": True})
    mock_ads_client.run_query.side_effect = [[_make_campaign_row()], []]
    pause_decision = {"decisions": [{"action_type": "pause_campaign", "target_id": "cmp111",
                                     "target_name": "Brand", "current_value": None,
                                     "recommended_value": None, "reasoning": "Low volume"}]}
    mock_claude_client.complete_json.return_value = (pause_decision, 60)
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.return_value = None
    agent = ManagerAgent(mock_ads_client, mock_claude_client, mock_db_session)
    with patch("agents.manager.build_client_context", return_value="ctx"), \
         patch("agents.manager.send_queue_summary"), \
         patch("agents.manager.write_queue_item") as mock_write:
        result = agent.run(account)
    mock_write.assert_not_called()
    assert result.decisions_generated == 0


# ── 5.3 Approval Queue Integrity ──────────────────────────────────────────────

def test_queue_approve_already_executed_raises(db_session):
    from db.models import Account as Acc, ApprovalQueue
    from db.queue import approve_item, write_queue_item
    from tests.factories import make_account

    account = Acc(**make_account({"customer_id": "MANAGER-INT-1"}))
    db_session.add(account)
    db_session.flush()

    item = write_queue_item(db_session, account.id, "manager", "increase_bid", {}, "test")
    item.status = "executed"
    db_session.flush()

    with pytest.raises(ValueError, match="cannot be approved"):
        approve_item(db_session, item.id, "user@test.com")


def test_queue_approve_already_rejected_raises(db_session):
    from db.models import Account as Acc
    from db.queue import approve_item, reject_item, write_queue_item
    from tests.factories import make_account

    account = Acc(**make_account({"customer_id": "MANAGER-INT-2"}))
    db_session.add(account)
    db_session.flush()

    item = write_queue_item(db_session, account.id, "manager", "increase_bid", {}, "test")
    reject_item(db_session, item.id, "user@test.com")

    with pytest.raises(ValueError, match="cannot be approved"):
        approve_item(db_session, item.id, "user2@test.com")
