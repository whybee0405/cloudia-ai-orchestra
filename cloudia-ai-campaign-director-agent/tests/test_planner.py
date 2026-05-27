"""Section 5b — Planner agent tests."""
import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from backend.agents.planner import PlannerAgent
from backend.agents.base import AgentError
from backend.db.models import ContentCalendar, ApprovalGate
from tests.factories import db_client, db_campaign, db_platform_account

# Planner expects claude.call_json to return a LIST of calendar items
CALENDAR_LIST = [
    {"platform": "instagram", "content_type": "image_post",
     "scheduled_for": "2026-06-01T09:00:00", "notes": "Post 1"},
    {"platform": "facebook", "content_type": "image_post",
     "scheduled_for": "2026-06-02T10:00:00", "notes": "Post 2"},
    {"platform": "instagram", "content_type": "reel",
     "scheduled_for": "2026-06-03T19:00:00", "notes": "Reel 1"},
]


def _make_planner(db):
    return PlannerAgent(db)


def _mock_calendar(items=None):
    return (items or CALENDAR_LIST, 100, 50, 0.003)


class TestPlannerCalendarGeneration:
    def test_creates_calendar_items(self, db):
        client = db_client(db)
        campaign = db_campaign(db, client.id)
        campaign.platforms = ["instagram", "facebook"]
        db.flush()
        for platform in ["instagram", "facebook"]:
            db_platform_account(db, client.id, platform)
        db.commit()

        with patch("backend.ai.claude.call_json", return_value=_mock_calendar()):
            _make_planner(db).run(campaign.id)

        items = db.query(ContentCalendar).filter_by(campaign_id=campaign.id).all()
        assert len(items) > 0

    def test_calendar_review_gate_created(self, db):
        client = db_client(db)
        campaign = db_campaign(db, client.id)
        campaign.platforms = ["instagram"]
        db.flush()
        db_platform_account(db, client.id, "instagram")
        db.commit()

        ig_items = [CALENDAR_LIST[0]]
        with patch("backend.ai.claude.call_json", return_value=_mock_calendar(ig_items)):
            _make_planner(db).run(campaign.id)

        gate = db.query(ApprovalGate).filter_by(campaign_id=campaign.id, gate_name="calendar_review").first()
        assert gate is not None
        assert gate.status == "pending"

    def test_campaign_status_set_to_calendar_review(self, db):
        client = db_client(db)
        campaign = db_campaign(db, client.id)
        campaign.platforms = ["instagram"]
        db.flush()
        db_platform_account(db, client.id, "instagram")
        db.commit()

        ig_items = [CALENDAR_LIST[0]]
        with patch("backend.ai.claude.call_json", return_value=_mock_calendar(ig_items)):
            _make_planner(db).run(campaign.id)

        db.refresh(campaign)
        assert campaign.status == "calendar_review"

    def test_unknown_platform_rejected(self, db):
        client = db_client(db)
        campaign = db_campaign(db, client.id)
        campaign.platforms = ["instagram"]
        db.flush()
        db_platform_account(db, client.id, "instagram")
        db.commit()

        bad_items = [
            {"platform": "myspace", "content_type": "image_post",
             "scheduled_for": "2026-06-01T09:00:00", "notes": "Test"},
        ]
        with patch("backend.ai.claude.call_json", return_value=_mock_calendar(bad_items)):
            _make_planner(db).run(campaign.id)

        items = db.query(ContentCalendar).filter_by(campaign_id=campaign.id).all()
        platforms = [i.platform for i in items]
        assert "myspace" not in platforms

    def test_duplicate_slots_deduplicated(self, db):
        """Two posts on same platform within 3h → only one kept or second shifted."""
        client = db_client(db)
        campaign = db_campaign(db, client.id)
        campaign.platforms = ["instagram"]
        db.flush()
        db_platform_account(db, client.id, "instagram")
        db.commit()

        duplicate_items = [
            {"platform": "instagram", "content_type": "image_post",
             "scheduled_for": "2026-06-01T09:00:00", "notes": "Post 1"},
            {"platform": "instagram", "content_type": "image_post",
             "scheduled_for": "2026-06-01T09:30:00", "notes": "Post 2 (within 3h)"},
        ]
        with patch("backend.ai.claude.call_json", return_value=_mock_calendar(duplicate_items)):
            _make_planner(db).run(campaign.id)

        items = db.query(ContentCalendar).filter_by(campaign_id=campaign.id, platform="instagram").all()
        assert len(items) >= 1

        if len(items) == 2:
            times = sorted([i.scheduled_for for i in items])
            diff = abs((times[1] - times[0]).total_seconds())
            assert diff >= 3 * 3600, f"Posts too close together: {diff}s"

    def test_planner_campaign_not_found(self, db):
        with pytest.raises(AgentError, match="not found"):
            _make_planner(db).run(99999)
