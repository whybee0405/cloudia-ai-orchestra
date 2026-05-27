"""Section 11 — API stress tests using FastAPI TestClient."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from api.app import create_app
from db.models import Account, ApprovalQueue
import config


# ── App factory with test DB override ─────────────────────────────────────────

@pytest.fixture()
def app(db_session):
    """FastAPI app with the DB session and client mocks injected for testing."""
    from unittest.mock import MagicMock
    from api.routes import _get_ads_client, _get_claude_client
    from db.session import get_db
    from google_ads.client import AdsClient
    from ai.claude import ClaudeClient

    mock_ads = MagicMock(spec=AdsClient)
    mock_claude = MagicMock(spec=ClaudeClient)
    mock_claude.complete_json.return_value = ({}, 0)
    mock_claude.estimate_cost_usd.return_value = 0.0

    application = create_app()
    application.dependency_overrides[get_db] = lambda: db_session
    application.dependency_overrides[_get_ads_client] = lambda: mock_ads
    application.dependency_overrides[_get_claude_client] = lambda: mock_claude
    return application


@pytest.fixture()
def client(app):
    return TestClient(app)


@pytest.fixture()
def authed_client(app):
    """Client with valid API key header."""
    return TestClient(app, headers={"X-API-Key": config.API_SECRET_KEY})


@pytest.fixture()
def account_in_db(db_session) -> Account:
    from tests.factories import make_account
    account = Account(**make_account({"customer_id": "API-TEST-001"}))
    db_session.add(account)
    db_session.flush()
    return account


@pytest.fixture()
def pending_item_in_db(db_session, account_in_db) -> ApprovalQueue:
    item = ApprovalQueue(
        account_id=account_in_db.id,
        agent_name="manager",
        action_type="increase_bid",
        action_payload={"target_id": "ag1"},
        reasoning="Test reason",
        status="pending",
    )
    db_session.add(item)
    db_session.flush()
    return item


# ── Health endpoint ────────────────────────────────────────────────────────────

def test_health_endpoint_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── Authentication ─────────────────────────────────────────────────────────────

def test_post_without_api_key_returns_401(client, pending_item_in_db):
    resp = client.post(f"/queue/{pending_item_in_db.id}/approve", json={"reviewed_by": "test"})
    assert resp.status_code == 401


def test_post_with_invalid_api_key_returns_401(client, pending_item_in_db):
    resp = client.post(
        f"/queue/{pending_item_in_db.id}/approve",
        json={"reviewed_by": "test"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401


def test_get_accounts_does_not_require_auth(client):
    """GET requests should be accessible without API key."""
    resp = client.get("/accounts")
    assert resp.status_code == 200


def test_get_queue_does_not_require_auth(client):
    resp = client.get("/queue")
    assert resp.status_code == 200


# ── Queue routes ───────────────────────────────────────────────────────────────

def test_get_queue_returns_pending_items(authed_client, pending_item_in_db):
    resp = authed_client.get("/queue")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(item["id"] == pending_item_in_db.id for item in data)


def test_get_queue_all_items_are_pending(authed_client, db_session, account_in_db):
    """GET /queue should only return items with status='pending'."""
    executed = ApprovalQueue(
        account_id=account_in_db.id, agent_name="manager",
        action_type="increase_bid", status="executed",
    )
    db_session.add(executed)
    db_session.flush()

    resp = authed_client.get("/queue")
    data = resp.json()
    for item in data:
        assert item["status"] == "pending"


def test_get_queue_item_not_found_returns_404(authed_client):
    resp = authed_client.get("/queue/99999")
    assert resp.status_code == 404


def test_approve_queue_item(authed_client, pending_item_in_db):
    resp = authed_client.post(
        f"/queue/{pending_item_in_db.id}/approve",
        json={"reviewed_by": "approver@test.com"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_approve_already_executed_returns_409(authed_client, db_session, account_in_db):
    item = ApprovalQueue(
        account_id=account_in_db.id, agent_name="manager",
        action_type="increase_bid", status="executed",
    )
    db_session.add(item)
    db_session.flush()

    resp = authed_client.post(f"/queue/{item.id}/approve", json={"reviewed_by": "test"})
    assert resp.status_code == 409


def test_reject_queue_item_requires_reviewed_by(authed_client, pending_item_in_db):
    resp = authed_client.post(f"/queue/{pending_item_in_db.id}/reject", json={})
    assert resp.status_code == 422


def test_reject_nonexistent_item_returns_404(authed_client):
    resp = authed_client.post("/queue/99999/reject", json={"reviewed_by": "test"})
    assert resp.status_code == 404


# ── Account routes ─────────────────────────────────────────────────────────────

def test_list_accounts(authed_client, account_in_db):
    resp = authed_client.get("/accounts")
    assert resp.status_code == 200
    data = resp.json()
    assert any(a["customer_id"] == account_in_db.customer_id for a in data)


def test_set_baseline_updates_account(authed_client, account_in_db):
    resp = authed_client.post(
        f"/accounts/{account_in_db.id}/baseline",
        json={"ctr": 0.045, "cpc": 18.50, "cpa": 390.0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == account_in_db.id


def test_set_baseline_nonexistent_account_returns_404(authed_client):
    resp = authed_client.post("/accounts/99999/baseline", json={"ctr": 0.04})
    assert resp.status_code == 404


# ── Campaign creation ──────────────────────────────────────────────────────────

def test_create_campaign_with_invalid_brief_returns_422(authed_client, account_in_db):
    """Missing required 'goal' field must return 422."""
    resp = authed_client.post(
        "/campaigns/create",
        json={
            "account_id": account_in_db.id,
            "brief": {
                # Missing 'goal', 'product_service', 'audience_description', 'landing_page_url'
                "budget_daily_zar": 200,
            },
        },
    )
    assert resp.status_code == 422


def test_create_campaign_with_zero_budget_returns_422(authed_client, account_in_db):
    """budget_daily_zar must be > 0."""
    resp = authed_client.post(
        "/campaigns/create",
        json={
            "account_id": account_in_db.id,
            "brief": {
                "goal": "generate leads",
                "product_service": "Dental services",
                "audience_description": "Adults in Cape Town",
                "budget_daily_zar": 0,
                "landing_page_url": "https://example.co.za",
            },
        },
    )
    assert resp.status_code == 422


# ── Audit log ──────────────────────────────────────────────────────────────────

def test_get_audit_log_returns_list(authed_client):
    resp = authed_client.get("/audit")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
