"""Section 7 — Keyword Scout stress tests."""

from unittest.mock import MagicMock, patch

import pytest

from agents.keyword_scout import KeywordScoutAgent


def _agent(ads=None, claude=None, db=None) -> KeywordScoutAgent:
    ads = ads or MagicMock()
    claude = claude or MagicMock()
    db = db or MagicMock()
    db.add.return_value = None
    db.commit.return_value = None
    return KeywordScoutAgent(ads, claude, db)


def test_scout_skips_when_no_search_terms(mock_ads_client, mock_claude_client, mock_db_session, sample_account):
    mock_ads_client.run_query.return_value = []
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    agent = _agent(mock_ads_client, mock_claude_client, mock_db_session)

    with patch("agents.keyword_scout.build_client_context", return_value="ctx"):
        result = agent.run(sample_account)

    assert result.status == "success"
    assert "skipped" in result.summary.lower()
    mock_claude_client.complete_json.assert_not_called()


def test_scout_writes_correct_action_types(mock_ads_client, mock_claude_client, mock_db_session, sample_account):
    """Each recommendation category maps to the correct action_type in the queue."""
    mock_ads_client.run_query.return_value = [MagicMock()]
    mock_claude_client.complete_json.return_value = ({
        "new_keyword_opportunities": [
            {"keyword_text": "emergency dentist", "match_type": "PHRASE",
             "ad_group_id": "ag1", "reasoning": "High intent"}
        ],
        "negatives_to_add": [
            {"keyword_text": "free dentist", "match_type": "BROAD",
             "campaign_id": "cam1", "reasoning": "Low quality"}
        ],
        "match_type_adjustments": [],
    }, 300)
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.scalars.return_value.first.return_value = None

    added_items = []

    def capture_add(obj):
        from db.models import ApprovalQueue
        if isinstance(obj, ApprovalQueue):
            added_items.append(obj)

    mock_db_session.add.side_effect = capture_add

    agent = _agent(mock_ads_client, mock_claude_client, mock_db_session)

    with patch("agents.keyword_scout.build_client_context", return_value="ctx"), \
         patch("agents.keyword_scout._parse_search_term_row", return_value={}), \
         patch("agents.keyword_scout._parse_keyword_row", return_value={}), \
         patch("agents.keyword_scout._build_scout_user_message", return_value="msg"):
        agent.execute(sample_account)

    action_types = {item.action_type for item in added_items}
    assert "add_keyword" in action_types
    assert "add_negative_keyword" in action_types


def test_scout_skips_malformed_recommendation_items(mock_ads_client, mock_claude_client, mock_db_session, sample_account):
    """Non-dict items in recommendation lists are skipped gracefully."""
    mock_ads_client.run_query.return_value = [MagicMock()]
    mock_claude_client.complete_json.return_value = ({
        "new_keyword_opportunities": ["not a dict", None, 42],
        "negatives_to_add": [],
        "match_type_adjustments": [],
    }, 200)
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.scalars.return_value.first.return_value = None

    agent = _agent(mock_ads_client, mock_claude_client, mock_db_session)

    with patch("agents.keyword_scout.build_client_context", return_value="ctx"), \
         patch("agents.keyword_scout._parse_search_term_row", return_value={}), \
         patch("agents.keyword_scout._parse_keyword_row", return_value={}), \
         patch("agents.keyword_scout._build_scout_user_message", return_value="msg"):
        result = agent.execute(sample_account)

    # Should succeed with 0 queue items (malformed items skipped)
    assert result.decisions_generated == 0


def test_scout_handles_empty_recommendation_response(mock_ads_client, mock_claude_client, mock_db_session, sample_account):
    mock_ads_client.run_query.return_value = [MagicMock()]
    mock_claude_client.complete_json.return_value = ({
        "new_keyword_opportunities": [],
        "negatives_to_add": [],
        "match_type_adjustments": [],
    }, 100)
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.scalars.return_value.first.return_value = None

    agent = _agent(mock_ads_client, mock_claude_client, mock_db_session)

    with patch("agents.keyword_scout.build_client_context", return_value="ctx"), \
         patch("agents.keyword_scout._parse_search_term_row", return_value={}), \
         patch("agents.keyword_scout._parse_keyword_row", return_value={}), \
         patch("agents.keyword_scout._build_scout_user_message", return_value="msg"):
        result = agent.execute(sample_account)

    assert result.decisions_generated == 0
    assert result.status == "success"
