"""Section 6 — Reporter stress tests."""

from unittest.mock import MagicMock, patch

import pytest

from agents.reporter import ReporterAgent
from db.models import Account


def _active_account(**overrides) -> Account:
    from tests.factories import make_account
    from datetime import datetime
    data = make_account({"customer_id": "RPT-001", "baseline_set_at": datetime(2025, 1, 1), **overrides})
    return Account(**data)


def _agent(ads=None, claude=None, db=None) -> ReporterAgent:
    ads = ads or MagicMock()
    claude = claude or MagicMock()
    db = db or MagicMock()
    db.add.return_value = None
    db.commit.return_value = None
    return ReporterAgent(ads, claude, db)


def test_reporter_skips_when_no_data(mock_ads_client, mock_claude_client, mock_db_session, sample_account):
    mock_ads_client.run_query.return_value = []
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    agent = _agent(mock_ads_client, mock_claude_client, mock_db_session)

    with patch("agents.reporter.build_client_context", return_value="ctx"):
        result = agent.run(sample_account)

    assert result.status == "success"
    assert "skipped" in result.summary.lower()
    mock_claude_client.complete_json.assert_not_called()


def test_reporter_paused_account_is_skipped(mock_ads_client, mock_claude_client, mock_db_session):
    account = _active_account(status="paused")
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    agent = _agent(mock_ads_client, mock_claude_client, mock_db_session)
    result = agent.run(account)
    assert result.status == "skipped"
    mock_ads_client.run_query.assert_not_called()


def test_reporter_with_all_zero_metrics_does_not_crash(mock_ads_client, mock_claude_client, mock_db_session, sample_account):
    row = MagicMock()
    row.campaign.id = "cam1"
    row.campaign.name = "Test Campaign"
    row.metrics.impressions = 0
    row.metrics.clicks = 0
    row.metrics.cost_micros = 0
    row.metrics.conversions = 0
    row.metrics.ctr = 0
    row.metrics.average_cpc = 0
    row.metrics.cost_per_conversion = 0
    row.metrics.conversions_from_interactions_rate = 0
    row.metrics.roas = 0

    mock_ads_client.run_query.return_value = [row]
    mock_claude_client.complete_json.return_value = ({"executive_summary": "No data"}, 100)
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.scalars.return_value.first.return_value = None

    agent = _agent(mock_ads_client, mock_claude_client, mock_db_session)

    with patch("agents.reporter.build_client_context", return_value="ctx"), \
         patch("agents.reporter.send_weekly_report", return_value=True):
        result = agent.run(sample_account)

    assert result.status == "success"


def test_reporter_email_failure_does_not_crash(mock_ads_client, mock_claude_client, mock_db_session, sample_account):
    row = MagicMock()
    row.campaign.id = "cam1"
    row.campaign.name = "Campaign"
    row.metrics.impressions = 1000
    row.metrics.clicks = 45
    row.metrics.cost_micros = 900_000_000
    row.metrics.conversions = 3
    row.metrics.ctr = 0.045
    row.metrics.average_cpc = 20_000_000
    row.metrics.cost_per_conversion = 300_000_000
    row.metrics.conversions_from_interactions_rate = 0.067
    row.metrics.roas = 0

    mock_ads_client.run_query.return_value = [row]
    mock_claude_client.complete_json.return_value = ({"executive_summary": "Good week"}, 200)
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.scalars.return_value.first.return_value = None

    agent = _agent(mock_ads_client, mock_claude_client, mock_db_session)

    with patch("agents.reporter.build_client_context", return_value="ctx"), \
         patch("agents.reporter.send_weekly_report", return_value=False):
        result = agent.run(sample_account)

    assert result.status == "success"
    assert "not sent" in result.summary


def test_reporter_cross_account_contamination_impossible(mock_ads_client, mock_claude_client, mock_db_session):
    """Each agent.run() call gets only the data for that specific account."""
    from tests.factories import make_account
    from datetime import datetime

    acct_a = Account(**make_account({"customer_id": "A001", "client_name": "Account A",
                                      "baseline_set_at": datetime(2025, 1, 1)}))
    acct_b = Account(**make_account({"customer_id": "B002", "client_name": "Account B",
                                      "baseline_set_at": datetime(2025, 1, 1)}))

    mock_ads_client.run_query.return_value = []
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    agent = _agent(mock_ads_client, mock_claude_client, mock_db_session)

    with patch("agents.reporter.build_client_context", return_value="ctx"):
        agent.run(acct_a)
        agent.run(acct_b)

    # run_query must have been called with the customer_id of each account
    calls = [str(c) for c in mock_ads_client.run_query.call_args_list]
    assert any("A001" in c for c in calls)
    assert any("B002" in c for c in calls)
