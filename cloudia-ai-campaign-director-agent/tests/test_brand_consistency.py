"""Section 9 — Brand consistency agent tests."""
import pytest
from unittest.mock import patch, MagicMock

from backend.agents.editing.brand_consistency import BrandConsistencyAgent
from backend.db.models import ContentAsset
from tests.factories import (
    db_client, db_campaign, db_brand_guidelines, db_content_asset, db_calendar_item
)


def _setup(db, asset_overrides=None, guideline_overrides=None, asset_type="text"):
    client = db_client(db)
    campaign = db_campaign(db, client.id)
    guidelines = db_brand_guidelines(db, client.id, guideline_overrides)
    # Use text asset type so _check_text() is called (image assets only call _check_image())
    asset = db_content_asset(db, campaign.id, client.id, asset_type=asset_type, overrides=asset_overrides)
    cal = db_calendar_item(db, campaign.id, client.id)
    cal.asset_id = asset.id
    db.flush()
    db.commit()
    return asset, guidelines, campaign, client


def _make_agent(db):
    return BrandConsistencyAgent(db)


class TestTextChecks:
    def test_forbidden_word_causes_high_failure(self, db):
        asset, guidelines, campaign, client = _setup(
            db,
            asset_overrides={"text_content": "Get cheap Korean car parts today! #sandtonauto #koreancarparts"},
            guideline_overrides={"forbidden_words": ["cheap"]},
        )

        with patch("backend.ai.claude.call_json",
                   return_value=({"issues": []}, 10, 5, 0.001)):
            _make_agent(db).run(asset.id)

        db.refresh(asset)
        assert asset.status == "brand_check_failed"

    def test_competitor_name_causes_critical_failure(self, db):
        asset, guidelines, campaign, client = _setup(
            db,
            asset_overrides={"text_content": "Better than SpeedParts — order today! #sandtonauto #koreancarparts"},
            guideline_overrides={"competitor_names": ["SpeedParts"], "forbidden_words": []},
        )

        with patch("backend.ai.claude.call_json",
                   return_value=({"issues": []}, 10, 5, 0.001)):
            _make_agent(db).run(asset.id)

        db.refresh(asset)
        assert asset.status == "brand_check_failed"

    def test_clean_caption_passes(self, db):
        asset, guidelines, campaign, client = _setup(
            db,
            asset_overrides={
                "text_content": "Premium Korean car parts with same-day delivery. Book today! #sandtonauto #koreancarparts"
            },
        )

        with patch("backend.ai.claude.call_json",
                   return_value=({"issues": []}, 10, 5, 0.001)):
            _make_agent(db).run(asset.id)

        db.refresh(asset)
        assert asset.status in ("approved_for_review", "approved")

    def test_medium_severity_passes_with_warning(self, db):
        """Missing CTA = MEDIUM → should pass but with a warning."""
        asset, guidelines, campaign, client = _setup(
            db,
            asset_overrides={
                "text_content": "Korean car parts delivered same-day. #sandtonauto #koreancarparts"
                # No CTA keywords like "book now", "shop now", etc.
            },
            # Enable CTA_required so the MEDIUM check fires
            guideline_overrides={"required_elements": {"cta_required": True}},
        )

        with patch("backend.ai.claude.call_json",
                   return_value=({"issues": []}, 10, 5, 0.001)):
            _make_agent(db).run(asset.id)

        db.refresh(asset)
        # MEDIUM severity → should NOT be brand_check_failed
        assert asset.status != "brand_check_failed"


class TestSeverityRouting:
    def test_critical_fails_asset(self, db):
        """Competitor name → CRITICAL → asset = brand_check_failed."""
        asset, guidelines, campaign, client = _setup(
            db,
            asset_overrides={"text_content": "AutoKing has nothing on us! #sandtonauto #koreancarparts"},
            guideline_overrides={"competitor_names": ["AutoKing"], "forbidden_words": []},
        )
        with patch("backend.ai.claude.call_json",
                   return_value=({"issues": []}, 10, 5, 0.001)):
            _make_agent(db).run(asset.id)
        db.refresh(asset)
        assert asset.status == "brand_check_failed"

    def test_high_fails_asset(self, db):
        """Forbidden word → HIGH → asset = brand_check_failed."""
        asset, guidelines, campaign, client = _setup(
            db,
            asset_overrides={"text_content": "Free Korean car parts! #sandtonauto #koreancarparts"},
            guideline_overrides={"forbidden_words": ["free"]},
        )
        with patch("backend.ai.claude.call_json",
                   return_value=({"issues": []}, 10, 5, 0.001)):
            _make_agent(db).run(asset.id)
        db.refresh(asset)
        assert asset.status == "brand_check_failed"

    def test_low_medium_passes(self, db):
        """LOW/MEDIUM issues → asset passes with warnings, not failed."""
        asset, guidelines, campaign, client = _setup(
            db,
            asset_overrides={
                "text_content": "Korean car parts delivered lol. #sandtonauto #koreancarparts"
            },
            guideline_overrides={"forbidden_words": [], "competitor_names": []},
        )
        # Tone check returns informal tone warning (LOW)
        with patch("backend.ai.claude.call_json",
                   return_value=({"issues": [{"field": "tone", "issue": "Too informal", "severity": "LOW"}]}, 10, 5, 0.001)):
            _make_agent(db).run(asset.id)
        db.refresh(asset)
        assert asset.status != "brand_check_failed"
