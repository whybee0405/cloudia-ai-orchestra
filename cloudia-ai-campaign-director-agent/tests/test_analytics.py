"""Section 14 — Analytics agent tests."""
import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from backend.agents.publishing.analytics import AnalyticsAgent
from backend.agents.base import AgentError
from backend.db.models import PostAnalytics
from tests.factories import (
    db_client, db_campaign, db_platform_account, db_calendar_item,
    db_content_asset, db_scheduled_post, db_published_post
)


def _setup_published(db, platform="instagram"):
    client = db_client(db)
    campaign = db_campaign(db, client.id)
    asset = db_content_asset(db, campaign.id, client.id)
    account = db_platform_account(db, client.id, platform)
    cal = db_calendar_item(db, campaign.id, client.id, platform)
    cal.asset_id = asset.id
    db.flush()
    sp = db_scheduled_post(db, cal.id, asset.id, account.id)
    sp.status = "published"
    pub = db_published_post(db, sp.id, platform)
    db.commit()
    return pub, account


class TestEngagementRate:
    def test_engagement_rate_calculated_correctly(self, db):
        pub, account = _setup_published(db)

        mock_raw = {"impressions": 1000, "reach": 800, "likes": 40, "comments": 5, "shares": 3, "saved": 10}

        with patch.object(AnalyticsAgent, "_fetch_analytics", return_value=mock_raw):
            result = AnalyticsAgent(db).run(pub.id, "24h")

        analytics = db.query(PostAnalytics).filter_by(published_post_id=pub.id).first()
        assert analytics is not None
        expected_rate = Decimal(str((40 + 5 + 3) / 800)).quantize(Decimal("0.0001"))
        assert analytics.engagement_rate == expected_rate

    def test_reach_zero_gives_none_not_crash(self, db):
        pub, account = _setup_published(db)

        mock_raw = {"impressions": 0, "reach": 0, "likes": 0, "comments": 0, "shares": 0}

        with patch.object(AnalyticsAgent, "_fetch_analytics", return_value=mock_raw):
            result = AnalyticsAgent(db).run(pub.id, "24h")

        analytics = db.query(PostAnalytics).filter_by(published_post_id=pub.id).first()
        assert analytics.engagement_rate is None

    def test_empty_analytics_stored_as_zeros(self, db):
        pub, account = _setup_published(db)

        with patch.object(AnalyticsAgent, "_fetch_analytics", return_value={}):
            result = AnalyticsAgent(db).run(pub.id, "24h")

        analytics = db.query(PostAnalytics).filter_by(published_post_id=pub.id).first()
        assert analytics is not None
        assert analytics.likes == 0 or analytics.likes is None

    def test_snapshot_type_stored(self, db):
        pub, account = _setup_published(db)

        mock_raw = {"reach": 500, "likes": 10, "comments": 2, "shares": 1}

        with patch.object(AnalyticsAgent, "_fetch_analytics", return_value=mock_raw):
            AnalyticsAgent(db).run(pub.id, "72h")

        analytics = db.query(PostAnalytics).filter_by(published_post_id=pub.id, snapshot_type="72h").first()
        assert analytics is not None

    def test_7d_underperforming_flagged(self, db, caplog):
        import logging
        pub, account = _setup_published(db)

        # engagement rate = (1 + 0 + 0) / 1000 = 0.001 < 0.005 threshold
        mock_raw = {"reach": 1000, "likes": 1, "comments": 0, "shares": 0}

        with patch.object(AnalyticsAgent, "_fetch_analytics", return_value=mock_raw):
            with caplog.at_level(logging.WARNING):
                AnalyticsAgent(db).run(pub.id, "7d")

        assert "nderperform" in caplog.text.lower() or "0.001" in caplog.text

    def test_inactive_account_skipped(self, db):
        pub, account = _setup_published(db)
        account.is_active = False
        db.commit()

        result = AnalyticsAgent(db).run(pub.id, "24h")
        assert result.get("skipped") is True

    def test_published_post_not_found_raises(self, db):
        agent = AnalyticsAgent(db)
        with pytest.raises(AgentError, match="not found"):
            agent.run(99999, "24h")
