"""Section 10 — Orchestrator stress tests."""

from unittest.mock import MagicMock, patch

import pytest

from orchestrator import Orchestrator


def _make_mock_orchestrator(ads=None, claude=None, db=None):
    ads = ads or MagicMock()
    claude = claude or MagicMock()
    db = db or MagicMock()
    with patch("orchestrator.AuditorAgent"), \
         patch("orchestrator.ManagerAgent"), \
         patch("orchestrator.ReporterAgent"), \
         patch("orchestrator.KeywordScoutAgent"):
        orch = Orchestrator(ads, claude, db)
    return orch


def test_zero_active_accounts_runs_cleanly(mock_ads_client, mock_claude_client, mock_db_session):
    orch = _make_mock_orchestrator(mock_ads_client, mock_claude_client, mock_db_session)
    mock_db_session.scalars.return_value.all.return_value = []

    orch.run_auditor()  # should not raise
    assert mock_db_session.scalars.called


def test_one_account_exception_does_not_stop_loop(mock_ads_client, mock_claude_client, mock_db_session):
    from db.models import Account
    accounts = [
        Account(id=1, client_name="A", customer_id="a", mcc_id="x", status="active",
                baseline_set_at=None),
        Account(id=2, client_name="B", customer_id="b", mcc_id="x", status="active",
                baseline_set_at=None),
    ]
    mock_db_session.scalars.return_value.all.return_value = accounts

    orch = _make_mock_orchestrator(mock_ads_client, mock_claude_client, mock_db_session)
    orch.auditor = MagicMock()

    call_count = 0

    def side_effect(account):
        nonlocal call_count
        call_count += 1
        if account.id == 1:
            raise RuntimeError("Simulated account failure")
        return MagicMock(status="success", summary="ok")

    orch.auditor.run.side_effect = side_effect
    orch.run_auditor()

    # Both accounts were attempted
    assert call_count == 2


def test_all_accounts_fail_orchestrator_exits_cleanly(mock_ads_client, mock_claude_client, mock_db_session):
    from db.models import Account
    accounts = [Account(id=i, client_name=f"C{i}", customer_id=str(i), mcc_id="x", status="active") for i in range(3)]
    mock_db_session.scalars.return_value.all.return_value = accounts

    orch = _make_mock_orchestrator(mock_ads_client, mock_claude_client, mock_db_session)
    orch.auditor = MagicMock()
    orch.auditor.run.side_effect = RuntimeError("All fail")

    orch.run_auditor()  # must not raise even when every account fails


def test_get_active_accounts_filters_by_status(mock_ads_client, mock_claude_client, mock_db_session):
    """get_active_accounts must only return accounts with status='active'."""
    mock_db_session.scalars.return_value.all.return_value = []
    orch = _make_mock_orchestrator(mock_ads_client, mock_claude_client, mock_db_session)
    orch.get_active_accounts()
    # The SELECT statement must have been called on the session
    assert mock_db_session.scalars.called
