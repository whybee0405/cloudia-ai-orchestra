"""Section 12 — Publisher agent tests including cross-client safety."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from backend.agents.publishing.publisher import PublisherAgent, SecurityError
from backend.agents.base import AgentError
from backend.db.models import PublishedPost, ScheduledPost
from tests.factories import (
    db_client, db_campaign, db_platform_account, db_calendar_item,
    db_content_asset, db_scheduled_post
)


def _setup_full_post(db, platform="instagram"):
    """Create a complete chain: client → campaign → account → calendar → asset → scheduled_post."""
    client = db_client(db)
    campaign = db_campaign(db, client.id, {"platforms": [platform]})
    asset = db_content_asset(db, campaign.id, client.id)
    asset.platform_versions = {platform: {"path": f"1/campaigns/1/raw/images/test.jpg", "caption": "Test caption"}}
    account = db_platform_account(db, client.id, platform)
    cal = db_calendar_item(db, campaign.id, client.id, platform)
    cal.asset_id = asset.id
    db.flush()
    sp = db_scheduled_post(db, cal.id, asset.id, account.id)
    db.commit()
    return client, campaign, account, cal, asset, sp


class TestCrossClientSafety:
    def test_account_wrong_client_raises_security_error(self, db):
        """CRITICAL: publisher must reject account.client_id != campaign.client_id."""
        client_a = db_client(db, {"name": "Client A"})
        client_b = db_client(db, {"name": "Client B"})

        campaign_a = db_campaign(db, client_a.id)
        asset = db_content_asset(db, campaign_a.id, client_a.id)
        cal = db_calendar_item(db, campaign_a.id, client_a.id)
        cal.asset_id = asset.id
        db.flush()

        # Account belongs to client_B but is used in client_A's scheduled post
        account_b = db_platform_account(db, client_b.id, "instagram")
        sp = db_scheduled_post(db, cal.id, asset.id, account_b.id)
        db.commit()

        publisher = PublisherAgent(db)
        with pytest.raises(SecurityError):
            publisher.run(sp.id)

    def test_account_correct_client_proceeds(self, db):
        client, campaign, account, cal, asset, sp = _setup_full_post(db)

        mock_post_id = "ig_123456789"

        with patch("backend.agents.publishing.publisher.PublisherAgent._post_to_platform",
                   return_value=mock_post_id):
            with patch("backend.agents.publishing.publisher.PublisherAgent._queue_analytics"):
                result = PublisherAgent(db).run(sp.id)

        assert result["platform_post_id"] == mock_post_id

        pub = db.query(PublishedPost).filter_by(scheduled_post_id=sp.id).first()
        assert pub is not None
        assert pub.platform_post_id == mock_post_id


class TestPreflightChecks:
    def test_inactive_account_fails(self, db):
        client, campaign, account, cal, asset, sp = _setup_full_post(db)
        account.is_active = False
        db.commit()

        publisher = PublisherAgent(db)
        with pytest.raises(AgentError, match="inactive"):
            publisher.run(sp.id)

    def test_expired_token_fails(self, db):
        client, campaign, account, cal, asset, sp = _setup_full_post(db)
        account.token_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()

        publisher = PublisherAgent(db)
        with pytest.raises(AgentError, match="[Tt]oken expired"):
            publisher.run(sp.id)

    def test_valid_token_no_expiry_proceeds(self, db):
        client, campaign, account, cal, asset, sp = _setup_full_post(db)
        account.token_expires_at = None  # No expiry — should proceed
        db.commit()

        with patch("backend.agents.publishing.publisher.PublisherAgent._post_to_platform",
                   return_value="ig_test"):
            with patch("backend.agents.publishing.publisher.PublisherAgent._queue_analytics"):
                result = PublisherAgent(db).run(sp.id)

        assert result["platform_post_id"] == "ig_test"

    def test_scheduled_post_not_found_raises(self, db):
        publisher = PublisherAgent(db)
        with pytest.raises(AgentError, match="not found"):
            publisher.run(99999)


class TestPostPublish:
    def test_published_post_record_created(self, db):
        client, campaign, account, cal, asset, sp = _setup_full_post(db)

        with patch("backend.agents.publishing.publisher.PublisherAgent._post_to_platform",
                   return_value="ig_post_123"):
            with patch("backend.agents.publishing.publisher.PublisherAgent._queue_analytics"):
                PublisherAgent(db).run(sp.id)

        pub = db.query(PublishedPost).filter_by(scheduled_post_id=sp.id).first()
        assert pub is not None
        assert pub.platform == "instagram"
        assert pub.platform_post_id == "ig_post_123"

    def test_scheduled_post_status_set_to_published(self, db):
        client, campaign, account, cal, asset, sp = _setup_full_post(db)

        with patch("backend.agents.publishing.publisher.PublisherAgent._post_to_platform",
                   return_value="ig_post_456"):
            with patch("backend.agents.publishing.publisher.PublisherAgent._queue_analytics"):
                PublisherAgent(db).run(sp.id)

        db.refresh(sp)
        assert sp.status == "published"

    def test_analytics_queued_after_publish(self, db):
        client, campaign, account, cal, asset, sp = _setup_full_post(db)

        analytics_calls = []

        def mock_queue(published_post_id):
            analytics_calls.append(published_post_id)

        with patch("backend.agents.publishing.publisher.PublisherAgent._post_to_platform",
                   return_value="ig_post_789"):
            with patch.object(PublisherAgent, "_queue_analytics", side_effect=mock_queue):
                PublisherAgent(db).run(sp.id)

        assert len(analytics_calls) == 1
