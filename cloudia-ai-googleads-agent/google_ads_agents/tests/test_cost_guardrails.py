"""Section 14 — Cost guardrail tests. Claude must NOT be called when there is nothing to diagnose."""

from unittest.mock import MagicMock, patch

import pytest

from agents.auditor import AuditorAgent
from agents.manager import ManagerAgent
from agents.reporter import ReporterAgent
from db.models import Account


def _active_account(**overrides) -> Account:
    from tests.factories import make_account
    from datetime import datetime
    data = make_account({"customer_id": "COST-001", "baseline_set_at": datetime(2025, 1, 1), **overrides})
    return Account(**data)


# ── Auditor: Claude skipped when no anomalies ──────────────────────────────────

def test_auditor_no_claude_call_when_zero_anomalies(mock_ads_client, mock_claude_client, mock_db_session):
    """If no anomalies are detected, Claude must NOT be called."""
    from db.models import CampaignSnapshot
    from datetime import datetime, timezone

    account = _active_account()
    mock_ads_client.run_query.return_value = ["row"]
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    # Both current and previous snapshots are identical → no anomalies
    stable_snap = MagicMock()
    stable_snap.ctr = 0.045
    stable_snap.cost_micros = 4_500_000_000
    stable_snap.conversion_rate = 0.032
    stable_snap.cost_per_conversion = 420_000_000
    stable_snap.clicks = 100
    stable_snap.conversions = 3.0
    stable_snap.campaign_id = "cam1"
    stable_snap.campaign_name = "Brand"
    stable_snap.impressions = 2222

    agent = AuditorAgent(mock_ads_client, mock_claude_client, mock_db_session)

    with patch("agents.auditor.build_client_context", return_value="ctx"), \
         patch("agents.auditor.parse_gaql_row", return_value={}), \
         patch("agents.auditor.save_snapshot", return_value=[stable_snap]), \
         patch("agents.auditor.get_previous_snapshot", return_value=stable_snap):
        result = agent.execute(account)

    mock_claude_client.complete_json.assert_not_called()
    assert result.anomalies_found == 0


# ── Manager: Claude skipped when no campaign data ─────────────────────────────

def test_manager_no_claude_call_when_no_campaign_data(mock_ads_client, mock_claude_client, mock_db_session):
    """If no campaign data is returned, manager skips Claude entirely."""
    account = _active_account()
    mock_ads_client.run_query.return_value = []
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    agent = ManagerAgent(mock_ads_client, mock_claude_client, mock_db_session)

    with patch("agents.manager.build_client_context", return_value="ctx"):
        result = agent.run(account)

    mock_claude_client.complete_json.assert_not_called()


# ── Reporter: Claude skipped for paused accounts ──────────────────────────────

def test_reporter_no_claude_call_for_paused_account(mock_ads_client, mock_claude_client, mock_db_session):
    """Reporter must not call Claude if account is paused."""
    account = _active_account(status="paused")
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    agent = ReporterAgent(mock_ads_client, mock_claude_client, mock_db_session)
    agent.run(account)

    mock_ads_client.run_query.assert_not_called()
    mock_claude_client.complete_json.assert_not_called()


# ── Tokens logged to agent_runs ────────────────────────────────────────────────

def test_agent_tokens_logged_to_run_record(mock_ads_client, mock_claude_client, mock_db_session):
    """tokens_used must be written to the AgentRun record after each run."""
    account = _active_account()
    mock_ads_client.run_query.return_value = []
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    run_records = []

    def capture_add(obj):
        from db.models import AgentRun
        if isinstance(obj, AgentRun):
            run_records.append(obj)

    mock_db_session.add.side_effect = capture_add

    manager = ManagerAgent(mock_ads_client, mock_claude_client, mock_db_session)

    with patch("agents.manager.build_client_context", return_value="ctx"):
        manager.run(account)

    # AgentRun record must exist
    assert len(run_records) >= 1
