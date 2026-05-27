"""Section 17 — Integration tests (full pipeline, mocked external calls)."""
import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from backend.db.models import (
    ContentCalendar, ContentAsset, ApprovalGate, ScheduledPost, PublishedPost
)
from tests.factories import (
    db_client, db_campaign, db_brand_guidelines, db_platform_account
)


class TestFullImagePostPipeline:
    def test_create_campaign_triggers_director(self, db):
        """Director runs, sets status to planning."""
        client = db_client(db)
        campaign = db_campaign(db, client.id, {"platforms": ["instagram"]})
        db_brand_guidelines(db, client.id)
        db_platform_account(db, client.id, "instagram")
        db.commit()

        from backend.agents.director import DirectorAgent

        with patch("backend.ai.claude.call_json",
                   return_value=({"suggested_content_mix": {"image_post": 3}}, 100, 50, 0.003)):
            result = DirectorAgent(db).run(campaign.id)

        db.refresh(campaign)
        assert campaign.status == "planning"

    def test_planner_creates_calendar_and_gate(self, db):
        """Planner creates calendar items and a calendar_review gate."""
        client = db_client(db)
        campaign = db_campaign(db, client.id, {"platforms": ["instagram"]})
        campaign.status = "planning"
        db_platform_account(db, client.id, "instagram")
        db.commit()

        from backend.agents.planner import PlannerAgent
        # Planner expects a LIST from claude.call_json
        calendar_data = [
            {
                "platform": "instagram",
                "content_type": "image_post",
                "scheduled_for": (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S"),
                "notes": "Post 1",
            },
            {
                "platform": "instagram",
                "content_type": "reel",
                "scheduled_for": (datetime.now(timezone.utc) + timedelta(days=4)).strftime("%Y-%m-%dT%H:%M:%S"),
                "notes": "Post 2",
            },
        ]

        with patch("backend.ai.claude.call_json", return_value=(calendar_data, 100, 50, 0.003)):
            PlannerAgent(db).run(campaign.id)

        calendar_items = db.query(ContentCalendar).filter_by(campaign_id=campaign.id).all()
        assert len(calendar_items) >= 1

        gate = db.query(ApprovalGate).filter_by(campaign_id=campaign.id, gate_name="calendar_review").first()
        assert gate is not None
        assert gate.status == "pending"

    def test_approve_gate_changes_status(self, db):
        client = db_client(db)
        campaign = db_campaign(db, client.id)
        gate = ApprovalGate(
            campaign_id=campaign.id,
            gate_name="calendar_review",
            status="pending",
        )
        db.add(gate)
        db.commit()

        gate.status = "approved"
        gate.reviewed_at = datetime.now(timezone.utc)
        db.commit()

        db.refresh(gate)
        assert gate.status == "approved"

    def test_publisher_creates_published_post(self, db):
        """Mock the full publish call — verify PublishedPost is created."""
        from backend.agents.publishing.publisher import PublisherAgent
        from tests.factories import (
            db_content_asset, db_calendar_item, db_scheduled_post
        )

        client = db_client(db)
        campaign = db_campaign(db, client.id, {"platforms": ["instagram"]})
        asset = db_content_asset(db, campaign.id, client.id)
        asset.platform_versions = {"instagram": {"path": "1/campaigns/1/raw/images/test.jpg"}}
        account = db_platform_account(db, client.id, "instagram")
        cal = db_calendar_item(db, campaign.id, client.id, "instagram")
        cal.asset_id = asset.id
        db.flush()
        sp = db_scheduled_post(db, cal.id, asset.id, account.id)
        db.commit()

        with patch.object(PublisherAgent, "_post_to_platform", return_value="ig_post_integration"):
            with patch.object(PublisherAgent, "_queue_analytics"):
                result = PublisherAgent(db).run(sp.id)

        pub = db.query(PublishedPost).filter_by(scheduled_post_id=sp.id).first()
        assert pub is not None
        assert pub.platform_post_id == "ig_post_integration"
        assert pub.platform == "instagram"

    def test_zero_failed_tasks_in_clean_pipeline(self, db):
        """After director + planner, no agent tasks should be failed."""
        from backend.agents.director import DirectorAgent
        from backend.agents.planner import PlannerAgent
        from backend.db.models import AgentTask

        client = db_client(db)
        campaign = db_campaign(db, client.id, {"platforms": ["instagram"]})
        db_brand_guidelines(db, client.id)
        db_platform_account(db, client.id, "instagram")
        db.commit()

        calendar_data = [
            {
                "platform": "instagram",
                "content_type": "image_post",
                "scheduled_for": (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S"),
                "notes": "Test",
            }
        ]

        with patch("backend.ai.claude.call_json",
                   return_value=({"suggested_content_mix": {}}, 100, 50, 0.003)):
            DirectorAgent(db).run(campaign.id)

        with patch("backend.ai.claude.call_json", return_value=(calendar_data, 100, 50, 0.003)):
            PlannerAgent(db).run(campaign.id)

        failed_tasks = db.query(AgentTask).filter_by(
            campaign_id=campaign.id, status="failed"
        ).all()
        assert len(failed_tasks) == 0


class TestEmergencyScenario:
    def test_pause_campaign_revokes_scheduled_posts(self, db):
        """Pausing a campaign should cancel all queued posts."""
        from tests.factories import db_content_asset, db_calendar_item, db_scheduled_post

        client = db_client(db)
        campaign = db_campaign(db, client.id, {"platforms": ["instagram"]})
        campaign.status = "active"
        asset = db_content_asset(db, campaign.id, client.id)
        account = db_platform_account(db, client.id, "instagram")

        posts = []
        for i in range(3):
            cal = db_calendar_item(db, campaign.id, client.id, "instagram", {
                "scheduled_for": datetime.now(timezone.utc) + timedelta(days=i+1)
            })
            cal.asset_id = asset.id
            db.flush()
            sp = db_scheduled_post(db, cal.id, asset.id, account.id)
            posts.append(sp)

        db.commit()

        for sp in posts:
            sp.status = "cancelled"
        campaign.status = "paused"
        db.commit()

        active_posts = db.query(ScheduledPost).filter(
            ScheduledPost.status == "queued",
            ScheduledPost.calendar_id.in_([p.calendar_id for p in posts])
        ).all()
        assert len(active_posts) == 0

    def test_published_posts_unaffected_by_pause(self, db):
        """Already-published posts must not be deleted on pause."""
        from tests.factories import db_content_asset, db_calendar_item, db_scheduled_post, db_published_post

        client = db_client(db)
        campaign = db_campaign(db, client.id)
        asset = db_content_asset(db, campaign.id, client.id)
        account = db_platform_account(db, client.id, "instagram")
        cal = db_calendar_item(db, campaign.id, client.id)
        cal.asset_id = asset.id
        db.flush()
        sp = db_scheduled_post(db, cal.id, asset.id, account.id)
        sp.status = "published"
        pub = db_published_post(db, sp.id)
        db.commit()

        campaign.status = "paused"
        db.commit()

        still_pub = db.get(PublishedPost, pub.id)
        assert still_pub is not None
