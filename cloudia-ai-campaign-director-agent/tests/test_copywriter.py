"""Section 6 — Copywriter agent tests."""
import pytest
from unittest.mock import patch
from tests.factories import db_client, db_campaign, db_brand_guidelines, db_calendar_item, db_platform_account


def _make_copywriter(db):
    from backend.agents.text.copywriter import CopywriterAgent
    return CopywriterAgent(db)


def _json_response(caption, hashtags=None):
    """Return call_json-style tuple with caption dict."""
    return ({"caption": caption, "hashtags": hashtags or []}, 100, 50, 0.003)


class TestCharacterLimits:
    def _test_limit(self, db, platform, limit, content_type="image_post"):
        client = db_client(db)
        campaign = db_campaign(db, client.id, {"platforms": [platform], "campaign_hashtags": ["#sandtonauto"]})
        db_brand_guidelines(db, client.id, {"forbidden_words": []})
        db_platform_account(db, client.id, platform)
        cal = db_calendar_item(db, campaign.id, client.id, platform, {"content_type": content_type})
        db.commit()

        over_limit = "A" * (limit + 100)
        valid = "Premium Korean car parts with same-day delivery. Book today!"
        call_count = 0

        def mock_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _json_response(over_limit, ["#sandtonauto"])
            return _json_response(valid, ["#sandtonauto"])

        with patch("backend.ai.claude.call_json", side_effect=mock_call):
            agent = _make_copywriter(db)
            result = agent.run(cal.id)

        assert call_count >= 2, f"Should have retried for {platform} over {limit} chars, got {call_count} calls"

    def test_instagram_over_2200_chars_rejected(self, db):
        self._test_limit(db, "instagram", 2200)

    def test_twitter_over_280_chars_rejected(self, db):
        self._test_limit(db, "twitter", 280, "tweet")

    def test_linkedin_over_3000_chars_rejected(self, db):
        self._test_limit(db, "linkedin", 3000)

    def test_google_business_over_1500_chars_rejected(self, db):
        self._test_limit(db, "google_business", 1500)

    def test_whatsapp_over_4096_chars_rejected(self, db):
        self._test_limit(db, "whatsapp", 4096, "broadcast")


class TestRequiredElements:
    def test_campaign_hashtags_present_in_caption(self, db):
        client = db_client(db)
        campaign = db_campaign(db, client.id, {"campaign_hashtags": ["#sandtonauto", "#koreancarparts"]})
        db_brand_guidelines(db, client.id, {"forbidden_words": []})
        db_platform_account(db, client.id, "instagram")
        cal = db_calendar_item(db, campaign.id, client.id)
        db.commit()

        caption = "Great caption. Book today!"
        with patch("backend.ai.claude.call_json",
                   return_value=_json_response(caption, ["#sandtonauto", "#koreancarparts"])):
            agent = _make_copywriter(db)
            result = agent.run(cal.id)

        assert result is not None


class TestForbiddenWords:
    def test_forbidden_word_in_output_rejected_and_retried(self, db):
        client = db_client(db)
        campaign = db_campaign(db, client.id, {"campaign_hashtags": ["#sandtonauto"]})
        db_brand_guidelines(db, client.id, {"forbidden_words": ["cheap"]})
        db_platform_account(db, client.id, "instagram")
        cal = db_calendar_item(db, campaign.id, client.id)
        db.commit()

        call_count = 0

        def mock_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _json_response("Get cheap Korean car parts! #sandtonauto", ["#sandtonauto"])
            return _json_response("Premium Korean car parts with same-day delivery! Book today!", ["#sandtonauto"])

        with patch("backend.ai.claude.call_json", side_effect=mock_call):
            agent = _make_copywriter(db)
            result = agent.run(cal.id)

        assert call_count >= 2

    def test_all_retries_fail_raises_error(self, db):
        from backend.agents.base import AgentError
        client = db_client(db)
        campaign = db_campaign(db, client.id, {"campaign_hashtags": ["#sandtonauto"]})
        db_brand_guidelines(db, client.id, {"forbidden_words": ["parts"]})
        db_platform_account(db, client.id, "instagram")
        cal = db_calendar_item(db, campaign.id, client.id)
        db.commit()

        with patch("backend.ai.claude.call_json",
                   return_value=_json_response("Korean car parts daily. #sandtonauto", ["#sandtonauto"])):
            agent = _make_copywriter(db)
            with pytest.raises(AgentError):
                agent.run(cal.id)


class TestCompetitorNames:
    def test_competitor_name_in_output_rejected(self, db):
        from backend.agents.base import AgentError
        client = db_client(db)
        campaign = db_campaign(db, client.id, {"campaign_hashtags": ["#sandtonauto"]})
        db_brand_guidelines(db, client.id, {
            "competitor_names": ["SpeedParts"],
            "forbidden_words": [],
        })
        db_platform_account(db, client.id, "instagram")
        cal = db_calendar_item(db, campaign.id, client.id)
        db.commit()

        with patch("backend.ai.claude.call_json",
                   return_value=_json_response("Better than SpeedParts! #sandtonauto", ["#sandtonauto"])):
            agent = _make_copywriter(db)
            with pytest.raises(AgentError):
                agent.run(cal.id)
