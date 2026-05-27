"""Section 4 — Auditor stress tests (calibration, thresholds, Claude failures)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from agents.auditor import AuditorAgent, _detect_anomalies
from agents.base import AgentRunResult
from db.models import Account
import config


def _make_snapshot(
    *,
    ctr: float = 0.05,
    cost_micros: int = 1_000_000,
    conversion_rate: float = 0.03,
    cost_per_conversion: float = 400.0,
    clicks: int = 100,
    conversions: float = 3.0,
    campaign_id: str = "cam1",
    campaign_name: str = "Test Campaign",
    impressions: int = 2000,
) -> MagicMock:
    snap = MagicMock()
    snap.ctr = ctr
    snap.cost_micros = cost_micros
    snap.conversion_rate = conversion_rate
    snap.cost_per_conversion = cost_per_conversion
    snap.clicks = clicks
    snap.conversions = conversions
    snap.campaign_id = campaign_id
    snap.campaign_name = campaign_name
    snap.impressions = impressions
    snap.avg_cpc_micros = 10_000_000
    snap.roas = None
    snap.budget_micros = 500_000_000
    snap.status = "ENABLED"
    return snap


_MODERATE = config.ANOMALY_THRESHOLDS["moderate"]
_CONSERVATIVE = config.ANOMALY_THRESHOLDS["conservative"]
_AGGRESSIVE = config.ANOMALY_THRESHOLDS["aggressive"]


# ── 4.1 Calibration Enforcement ────────────────────────────────────────────────

def test_auditor_skips_baseline_set_at_none(mock_ads_client, mock_claude_client, mock_db_session):
    account = Account(id=1, client_name="X", customer_id="x", mcc_id="y", baseline_set_at=None, status="active")
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    agent = AuditorAgent(mock_ads_client, mock_claude_client, mock_db_session)
    result = agent.run(account)
    assert result.status == "skipped"
    mock_ads_client.run_query.assert_not_called()


def test_auditor_skips_15_days_calibrating(mock_ads_client, mock_claude_client, mock_db_session):
    account = Account(
        id=2, client_name="X", customer_id="x2", mcc_id="y", status="active",
        baseline_set_at=datetime.now(timezone.utc) - timedelta(days=15),
    )
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    agent = AuditorAgent(mock_ads_client, mock_claude_client, mock_db_session)
    result = agent.run(account)
    assert result.status == "skipped"


def test_auditor_skips_29_days_calibrating(mock_ads_client, mock_claude_client, mock_db_session):
    account = Account(
        id=3, client_name="X", customer_id="x3", mcc_id="y", status="active",
        baseline_set_at=datetime.now(timezone.utc) - timedelta(days=29),
    )
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    agent = AuditorAgent(mock_ads_client, mock_claude_client, mock_db_session)
    result = agent.run(account)
    assert result.status == "skipped"


def test_auditor_runs_at_30_days(mock_ads_client, mock_claude_client, mock_db_session, sample_account):
    sample_account.baseline_set_at = datetime.now(timezone.utc) - timedelta(days=30)
    mock_ads_client.run_query.return_value = []
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.scalars.return_value.first.return_value = None
    agent = AuditorAgent(mock_ads_client, mock_claude_client, mock_db_session)

    with patch("agents.auditor.build_client_context", return_value="ctx"), \
         patch("agents.auditor.save_snapshot", return_value=[]), \
         patch("agents.auditor.get_previous_snapshot", return_value=None):
        result = agent.run(sample_account)

    assert result.status == "success"


# ── 4.2 Snapshot Logic ─────────────────────────────────────────────────────────

def test_first_run_no_previous_snapshot_no_anomalies(mock_ads_client, mock_claude_client, mock_db_session, sample_account):
    snap = _make_snapshot()
    mock_ads_client.run_query.return_value = ["row"]
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    agent = AuditorAgent(mock_ads_client, mock_claude_client, mock_db_session)

    with patch("agents.auditor.build_client_context", return_value="ctx"), \
         patch("agents.auditor.parse_gaql_row", return_value={}), \
         patch("agents.auditor.save_snapshot", return_value=[snap]), \
         patch("agents.auditor.get_previous_snapshot", return_value=None):
        result = agent.run(sample_account)

    assert result.anomalies_found == 0
    mock_claude_client.complete_json.assert_not_called()


# ── 4.3 Anomaly Detection Thresholds ──────────────────────────────────────────

def test_conservative_ctr_19pct_drop_no_anomaly():
    prev = _make_snapshot(ctr=0.10)
    curr = _make_snapshot(ctr=0.081)  # -19% drop (below 20% conservative threshold)
    assert not any(a["anomaly_type"] == "ctr_drop" for a in _detect_anomalies(curr, prev, _CONSERVATIVE))


def test_conservative_ctr_30pct_drop_anomaly():
    prev = _make_snapshot(ctr=0.10)
    curr = _make_snapshot(ctr=0.069)  # >30% drop
    anomalies = _detect_anomalies(curr, prev, _CONSERVATIVE)
    assert any(a["anomaly_type"] == "ctr_drop" for a in anomalies)


def test_aggressive_ctr_39pct_drop_no_anomaly():
    prev = _make_snapshot(ctr=0.10)
    curr = _make_snapshot(ctr=0.061)  # -39% drop (below 40% aggressive threshold)
    assert not any(a["anomaly_type"] == "ctr_drop" for a in _detect_anomalies(curr, prev, _AGGRESSIVE))


def test_aggressive_ctr_40pct_drop_anomaly():
    prev = _make_snapshot(ctr=0.10)
    curr = _make_snapshot(ctr=0.059)  # >40% drop
    anomalies = _detect_anomalies(curr, prev, _AGGRESSIVE)
    assert any(a["anomaly_type"] == "ctr_drop" for a in anomalies)


def test_spend_spike_below_threshold_no_anomaly():
    # Conservative threshold is 25%. 24% increase should not trigger.
    prev = _make_snapshot(cost_micros=1_000_000)
    curr = _make_snapshot(cost_micros=1_240_000)  # +24%
    assert not any(a["anomaly_type"] == "spend_spike" for a in _detect_anomalies(curr, prev, _CONSERVATIVE))


def test_spend_spike_above_threshold_anomaly():
    prev = _make_snapshot(cost_micros=1_000_000)
    curr = _make_snapshot(cost_micros=1_260_000)  # +26%
    anomalies = _detect_anomalies(curr, prev, _CONSERVATIVE)
    assert any(a["anomaly_type"] == "spend_spike" for a in anomalies)


def test_spend_spike_zero_previous_does_not_crash():
    prev = _make_snapshot(cost_micros=0)
    curr = _make_snapshot(cost_micros=1_000_000)
    # Should not raise ZeroDivisionError
    anomalies = _detect_anomalies(curr, prev, _MODERATE)
    assert not any(a["anomaly_type"] == "spend_spike" for a in anomalies)


def test_zero_conversions_with_low_clicks_no_anomaly():
    """Less than threshold clicks — not enough data."""
    curr = _make_snapshot(clicks=10, conversions=0, cost_micros=500_000)
    prev = _make_snapshot(clicks=10, conversions=2, cost_micros=500_000)
    anomalies = _detect_anomalies(curr, prev, _MODERATE)
    assert not any(a["anomaly_type"] == "zero_conversions" for a in anomalies)


def test_zero_conversions_with_high_clicks_and_spend_anomaly():
    """Many clicks, spending, zero conversions — anomaly."""
    curr = _make_snapshot(clicks=25, conversions=0, cost_micros=5_000_000)
    prev = _make_snapshot(clicks=25, conversions=3, cost_micros=4_000_000)
    anomalies = _detect_anomalies(curr, prev, _MODERATE)
    assert any(a["anomaly_type"] == "zero_conversions" for a in anomalies)


def test_zero_spend_zero_conversions_no_anomaly():
    """Not spending at all — not an issue."""
    curr = _make_snapshot(clicks=0, conversions=0, cost_micros=0)
    prev = _make_snapshot(clicks=0, conversions=0, cost_micros=0)
    anomalies = _detect_anomalies(curr, prev, _MODERATE)
    assert not any(a["anomaly_type"] == "zero_conversions" for a in anomalies)


# ── Legacy tests ────────────────────────────────────────────────────────────────

def test_auditor_skips_calibrating_account(mock_ads_client, mock_claude_client, mock_db_session):
    account = Account(id=99, client_name="X", customer_id="9999999999", mcc_id="0", status="active", baseline_set_at=None)
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    agent = AuditorAgent(mock_ads_client, mock_claude_client, mock_db_session)
    result = agent.run(account)
    assert result.status == "skipped"
    mock_ads_client.run_query.assert_not_called()


def test_auditor_no_campaigns(mock_ads_client, mock_claude_client, mock_db_session, sample_account):
    mock_ads_client.run_query.return_value = []
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    agent = AuditorAgent(mock_ads_client, mock_claude_client, mock_db_session)
    with patch("agents.auditor.build_client_context", return_value="ctx"):
        result = agent.run(sample_account)
    assert result.status == "success"
    assert "No campaigns" in result.summary
    mock_claude_client.complete_json.assert_not_called()


def test_detect_anomalies_ctr_drop():
    previous = _make_snapshot(ctr=0.10)
    current = _make_snapshot(ctr=0.06)
    anomalies = _detect_anomalies(current, previous, _MODERATE)
    assert any(a["anomaly_type"] == "ctr_drop" for a in anomalies)


def test_detect_anomalies_no_anomaly():
    previous = _make_snapshot(ctr=0.05, cost_micros=1_000_000, conversion_rate=0.03, cost_per_conversion=400.0, clicks=50, conversions=2.0)
    current = _make_snapshot(ctr=0.051, cost_micros=1_010_000, conversion_rate=0.031, cost_per_conversion=402.0, clicks=50, conversions=2.0)
    assert _detect_anomalies(current, previous, _MODERATE) == []


def test_detect_anomalies_spend_spike():
    previous = _make_snapshot(cost_micros=1_000_000)
    current = _make_snapshot(cost_micros=1_500_000)
    anomalies = _detect_anomalies(current, previous, _MODERATE)
    assert any(a["anomaly_type"] == "spend_spike" for a in anomalies)


# ── 4.5 Claude Failure Handling ────────────────────────────────────────────────

def test_auditor_claude_malformed_json_writes_audit_log(mock_ads_client, mock_claude_client, mock_db_session, sample_account):
    """Malformed Claude JSON still writes to audit_log with diagnosis='Claude response malformed'."""
    snap = _make_snapshot()
    previous = _make_snapshot(ctr=0.10)
    snap.ctr = 0.06  # -40% drop
    mock_ads_client.run_query.return_value = ["row"]
    mock_claude_client.complete_json.side_effect = ValueError("Claude returned non-JSON")
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    agent = AuditorAgent(mock_ads_client, mock_claude_client, mock_db_session)

    with patch("agents.auditor.build_client_context", return_value="ctx"), \
         patch("agents.auditor.parse_gaql_row", return_value={}), \
         patch("agents.auditor.save_snapshot", return_value=[snap]), \
         patch("agents.auditor.get_previous_snapshot", return_value=previous):
        result = agent.run(sample_account)

    # Must not crash; audit_log entry must be written
    mock_db_session.add.assert_called()
    assert result.status == "success"


def test_auditor_claude_network_exception_writes_audit_log(mock_ads_client, mock_claude_client, mock_db_session, sample_account):
    """Network exception from Claude still writes to audit_log."""
    snap = _make_snapshot()
    previous = _make_snapshot(ctr=0.10)
    snap.ctr = 0.06
    mock_ads_client.run_query.return_value = ["row"]
    mock_claude_client.complete_json.side_effect = ConnectionError("Network down")
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    agent = AuditorAgent(mock_ads_client, mock_claude_client, mock_db_session)

    with patch("agents.auditor.build_client_context", return_value="ctx"), \
         patch("agents.auditor.parse_gaql_row", return_value={}), \
         patch("agents.auditor.save_snapshot", return_value=[snap]), \
         patch("agents.auditor.get_previous_snapshot", return_value=previous):
        result = agent.run(sample_account)

    mock_db_session.add.assert_called()


# ── 4.6 Multi-Account Isolation ────────────────────────────────────────────────

def test_detect_anomalies_threshold_does_not_leak_between_accounts():
    """Conservative and aggressive thresholds are independent per account."""
    prev = _make_snapshot(ctr=0.10)
    curr_moderate_drop = _make_snapshot(ctr=0.075)  # -25%

    conservative_anomalies = _detect_anomalies(curr_moderate_drop, prev, _CONSERVATIVE)
    aggressive_anomalies = _detect_anomalies(curr_moderate_drop, prev, _AGGRESSIVE)

    # Conservative threshold is 20% → triggers
    assert any(a["anomaly_type"] == "ctr_drop" for a in conservative_anomalies)
    # Aggressive threshold is 40% → does NOT trigger for a 25% drop
    assert not any(a["anomaly_type"] == "ctr_drop" for a in aggressive_anomalies)
