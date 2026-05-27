"""Section 18 — Performance tests (timing bounds)."""
import time
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from tests.factories import db_client, db_campaign, db_brand_guidelines


class TestContextBuilderPerformance:
    def test_context_builder_under_10ms(self, db):
        from backend.ai.context_builder import build_campaign_context

        client = db_client(db)
        campaign = db_campaign(db, client.id)
        guidelines = db_brand_guidelines(db, client.id)
        db.commit()

        start = time.perf_counter()
        for _ in range(10):
            build_campaign_context(client, campaign, guidelines)
        elapsed_ms = (time.perf_counter() - start) * 1000 / 10

        assert elapsed_ms < 10, f"context_builder took {elapsed_ms:.1f}ms (limit: 10ms)"

    def test_estimate_tokens_fast(self, db):
        from backend.ai.context_builder import estimate_tokens

        text = "Sample text for token estimation. " * 200

        start = time.perf_counter()
        for _ in range(100):
            estimate_tokens(text)
        elapsed_ms = (time.perf_counter() - start) * 1000 / 100

        assert elapsed_ms < 1, f"estimate_tokens took {elapsed_ms:.2f}ms per call"


class TestBrandConsistencyPerformance:
    def test_brand_check_under_10_seconds(self, db):
        from backend.agents.editing.brand_consistency import BrandConsistencyAgent
        from tests.factories import db_calendar_item, db_content_asset

        client = db_client(db)
        campaign = db_campaign(db, client.id)
        guidelines = db_brand_guidelines(db, client.id)
        asset = db_content_asset(db, campaign.id, client.id, overrides={
            "text_content": "Premium Korean car parts. Book today! #sandtonauto #koreancarparts"
        })
        cal = db_calendar_item(db, campaign.id, client.id)
        cal.asset_id = asset.id
        db.commit()

        start = time.perf_counter()
        with patch("backend.ai.claude.call_json",
                   return_value=({"issues": []}, 10, 5, 0.001)):
            BrandConsistencyAgent(db).run(asset.id)
        elapsed = time.perf_counter() - start

        assert elapsed < 10, f"Brand consistency check took {elapsed:.1f}s (limit: 10s)"


class TestDatabaseQueryPerformance:
    def test_campaign_list_query_fast(self, db):
        """Simple campaign query should be fast even without 50 records in SQLite."""
        client = db_client(db)
        for i in range(10):
            db_campaign(db, client.id, {"name": f"Campaign {i}"})
        db.commit()

        start = time.perf_counter()
        from backend.db.models import Campaign
        campaigns = db.query(Campaign).filter_by(client_id=client.id).limit(50).all()
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 500, f"Campaign list query took {elapsed_ms:.0f}ms"
        assert len(campaigns) == 10
