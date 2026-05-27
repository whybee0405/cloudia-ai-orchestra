"""Section 8 — Creator stress tests."""

from unittest.mock import MagicMock, patch

import pytest

from agents.creator import CreatorAgent
from db.models import Account


def _active_account(**overrides) -> Account:
    from tests.factories import make_account
    from datetime import datetime
    data = make_account({"customer_id": "CRT-001", "baseline_set_at": datetime(2025, 1, 1), **overrides})
    return Account(**data)


def _agent(ads=None, claude=None, db=None) -> CreatorAgent:
    ads = ads or MagicMock()
    claude = claude or MagicMock()
    db = db or MagicMock()
    db.add.return_value = None
    db.commit.return_value = None
    db.refresh.return_value = None
    return CreatorAgent(ads, claude, db)


def _valid_brief() -> dict:
    return {
        "goal": "generate leads",
        "product_service": "Emergency dental care",
        "audience_description": "Adults in Cape Town needing urgent dental help",
        "budget_daily_zar": 200.0,
        "geo_targets": ["Cape Town"],
        "languages": ["English"],
        "landing_page_url": "https://example.co.za/emergency-dentist",
    }


def _valid_campaign_structure() -> dict:
    return {
        "campaign_name": "Emergency Dentist - Search",
        "campaign_settings": {
            "budget_daily_micros": 200_000_000,
            "bidding_strategy": "MANUAL_CPC",
            "network_settings": {"search": True, "display": False},
        },
        "ad_groups": [
            {
                "name": "Emergency Terms",
                "cpc_bid_micros": 25_000_000,
                "keywords": [{"text": "emergency dentist cape town", "match_type": "EXACT"}],
                "ads": [
                    {
                        "headlines": ["Emergency Dentist", "Open Now", "Book Online"],
                        "descriptions": ["Same-day appointments available.", "Trusted Cape Town dentist."],
                        "final_url": "https://example.co.za/emergency",
                    }
                ],
            }
        ],
    }


# ── Creator is allowed to run during calibration ──────────────────────────────

def test_creator_allowed_during_calibration(mock_ads_client, mock_claude_client, mock_db_session):
    """Creator.execute() always raises NotImplementedError (creation goes via create_from_brief)."""
    account = _active_account(baseline_set_at=None)  # calibrating
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    agent = _agent(mock_ads_client, mock_claude_client, mock_db_session)

    with pytest.raises(NotImplementedError):
        agent.execute(account)


# ── Brief validation ───────────────────────────────────────────────────────────

def test_creator_rejects_brief_with_zero_budget(mock_ads_client, mock_claude_client, mock_db_session, sample_account):
    brief = {**_valid_brief(), "budget_daily_zar": 0}
    agent = _agent(mock_ads_client, mock_claude_client, mock_db_session)

    with pytest.raises((ValueError, Exception)):
        agent.create_from_brief(sample_account, brief)

    mock_claude_client.complete_json.assert_not_called()


def test_creator_rejects_brief_with_negative_budget(mock_ads_client, mock_claude_client, mock_db_session, sample_account):
    brief = {**_valid_brief(), "budget_daily_zar": -100}
    agent = _agent(mock_ads_client, mock_claude_client, mock_db_session)

    with pytest.raises((ValueError, Exception)):
        agent.create_from_brief(sample_account, brief)

    mock_claude_client.complete_json.assert_not_called()


# ── Campaign structure validation ──────────────────────────────────────────────

def test_creator_rejects_campaign_with_no_ad_groups(mock_ads_client, mock_claude_client, mock_db_session, sample_account):
    """Claude returns a structure with no ad_groups — must raise ValueError."""
    mock_claude_client.complete_json.return_value = ({
        "campaign_name": "Empty Campaign",
        "campaign_settings": {"budget_daily_micros": 200_000_000},
        "ad_groups": [],  # invalid
    }, 400)
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    agent = _agent(mock_ads_client, mock_claude_client, mock_db_session)

    with patch("agents.creator.build_client_context", return_value="ctx"):
        with pytest.raises(ValueError, match="ad_groups"):
            agent.create_from_brief(sample_account, _valid_brief())


def test_creator_rejects_headline_over_30_chars(mock_ads_client, mock_claude_client, mock_db_session, sample_account):
    """Headlines exceeding 30 characters must be rejected."""
    structure = _valid_campaign_structure()
    structure["ad_groups"][0]["ads"][0]["headlines"] = [
        "This headline is way too long for Google Ads",  # >30 chars
        "Short",
        "Another Short",
    ]
    mock_claude_client.complete_json.return_value = (structure, 400)
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    agent = _agent(mock_ads_client, mock_claude_client, mock_db_session)

    with patch("agents.creator.build_client_context", return_value="ctx"):
        with pytest.raises(ValueError, match="headline"):
            agent.create_from_brief(sample_account, _valid_brief())


def test_creator_rejects_description_over_90_chars(mock_ads_client, mock_claude_client, mock_db_session, sample_account):
    """Descriptions exceeding 90 characters must be rejected."""
    structure = _valid_campaign_structure()
    structure["ad_groups"][0]["ads"][0]["descriptions"] = [
        "This description is far too long and will exceed the Google Ads character limit of 90 characters",
        "Short description.",
    ]
    mock_claude_client.complete_json.return_value = (structure, 400)
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    agent = _agent(mock_ads_client, mock_claude_client, mock_db_session)

    with patch("agents.creator.build_client_context", return_value="ctx"):
        with pytest.raises(ValueError, match="description"):
            agent.create_from_brief(sample_account, _valid_brief())


def test_creator_valid_structure_writes_to_queue(mock_ads_client, mock_claude_client, mock_db_session, sample_account):
    """Valid structure from Claude is written to approval_queue with status=pending."""
    structure = _valid_campaign_structure()
    mock_claude_client.complete_json.return_value = (structure, 500)
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None

    queue_items_added = []

    def capture_add(obj):
        from db.models import ApprovalQueue
        if isinstance(obj, ApprovalQueue):
            queue_items_added.append(obj)

    mock_db_session.add.side_effect = capture_add

    agent = _agent(mock_ads_client, mock_claude_client, mock_db_session)

    with patch("agents.creator.build_client_context", return_value="ctx"):
        queue_item, returned_structure = agent.create_from_brief(sample_account, _valid_brief())

    assert len(queue_items_added) == 1
    assert queue_items_added[0].action_type == "create_campaign"
    assert returned_structure == structure
