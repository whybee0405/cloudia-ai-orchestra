"""Section 5a — Director agent tests."""
import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from backend.agents.director import DirectorAgent
from backend.agents.base import AgentError
from tests.factories import db_client, db_campaign, db_platform_account, db_brand_guidelines


class TestDirectorValidation:
    def _make_director(self, db):
        return DirectorAgent(db)

    def test_missing_platform_account_halts(self, db):
        from backend.agents.base import AgentError
        client = db_client(db)
        # Campaign requires instagram + facebook but no accounts connected
        campaign = db_campaign(db, client.id)
        campaign.platforms = ["instagram", "facebook"]
        db.commit()

        director = self._make_director(db)
        with pytest.raises(AgentError, match="[Mm]issing"):
            director.run(campaign.id)

    def test_all_accounts_present_proceeds(self, db):
        client = db_client(db)
        campaign = db_campaign(db, client.id)
        campaign.platforms = ["instagram"]
        db.flush()
        db_platform_account(db, client.id, "instagram")
        db.commit()

        director = self._make_director(db)
        mock_response = '{"content_mix": {"image_post": 3, "reel": 2}}'
        with patch("backend.ai.claude.call_json", return_value=({"suggested_content_mix": {}}, 10, 5, 0.001)):
            result = director.run(campaign.id)

        assert campaign.status == "planning"

    def test_empty_brief_halts(self, db):
        client = db_client(db)
        campaign = db_campaign(db, client.id, {"brief": {}})
        campaign.platforms = ["instagram"]
        db.flush()
        db_platform_account(db, client.id, "instagram")
        db.commit()

        director = self._make_director(db)
        with pytest.raises(AgentError, match="brief"):
            director.run(campaign.id)

    def test_end_date_before_start_date_fails(self, db):
        client = db_client(db)
        campaign = db_campaign(db, client.id)
        campaign.start_date = date.today() + timedelta(days=10)
        campaign.end_date = date.today()
        campaign.platforms = ["instagram"]
        db.flush()
        db_platform_account(db, client.id, "instagram")
        db.commit()

        director = self._make_director(db)
        with pytest.raises(AgentError):
            director.run(campaign.id)

    def test_posts_per_week_zero_fails(self, db):
        client = db_client(db)
        campaign = db_campaign(db, client.id, {"posts_per_week": 0})
        campaign.platforms = ["instagram"]
        db.flush()
        db_platform_account(db, client.id, "instagram")
        db.commit()

        director = self._make_director(db)
        with pytest.raises(AgentError):
            director.run(campaign.id)

    def test_campaign_not_found_raises(self, db):
        director = self._make_director(db)
        with pytest.raises(AgentError, match="not found"):
            director.run(99999)
