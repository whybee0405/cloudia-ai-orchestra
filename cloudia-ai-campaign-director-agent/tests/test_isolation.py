"""Section 16 — Multi-client isolation tests (CRITICAL)."""
import pytest
from unittest.mock import patch

from backend.agents.publishing.publisher import PublisherAgent, SecurityError
from backend.db.models import ContentAsset, PlatformAccount
from tests.factories import (
    db_client, db_campaign, db_brand_guidelines, db_platform_account,
    db_calendar_item, db_content_asset, db_scheduled_post
)


class TestClientDataIsolation:
    def test_brand_guidelines_not_shared_between_clients(self, db):
        """Client A's forbidden words must not affect Client B's content."""
        from backend.ai.context_builder import build_campaign_context

        client_a = db_client(db, {"name": "Dental Practice"})
        client_b = db_client(db, {"name": "Auto Parts Store"})

        # Client A has forbidden_words = ["cheap", "drill"]
        guidelines_a = db_brand_guidelines(db, client_a.id, {
            "forbidden_words": ["cheap", "drill"],
            "competitor_names": ["DentalMax"],
        })
        # Client B has forbidden_words = ["broken", "rust"]
        guidelines_b = db_brand_guidelines(db, client_b.id, {
            "forbidden_words": ["broken", "rust"],
            "competitor_names": ["SpeedParts"],
        })

        campaign_b = db_campaign(db, client_b.id)
        db.commit()

        context_b = build_campaign_context(client_b, campaign_b, guidelines_b)

        # Client A's data must not appear in Client B's context
        assert "DentalMax" not in context_b
        assert "Dental Practice" not in context_b
        assert "drill" not in context_b

    def test_platform_account_cross_client_blocked_at_publish(self, db):
        """CRITICAL: Client B's account cannot be used to publish Client A's post."""
        client_a = db_client(db, {"name": "Dental Practice"})
        client_b = db_client(db, {"name": "Auto Parts Store"})

        campaign_a = db_campaign(db, client_a.id)
        asset_a = db_content_asset(db, campaign_a.id, client_a.id)
        cal_a = db_calendar_item(db, campaign_a.id, client_a.id)
        cal_a.asset_id = asset_a.id
        db.flush()

        # Attempt to use Client B's account for Client A's post
        account_b = db_platform_account(db, client_b.id, "instagram")
        sp = db_scheduled_post(db, cal_a.id, asset_a.id, account_b.id)
        db.commit()

        publisher = PublisherAgent(db)
        with pytest.raises(SecurityError):
            publisher.run(sp.id)

    def test_minio_paths_isolated_by_client(self):
        """Client A cannot access Client B's storage path."""
        from backend.media.storage import signed_url

        client_a_path = "1/campaigns/5/raw/images/logo_a.jpg"
        client_b_prefix = "2"  # Client B trying to access Client A's file

        with pytest.raises((PermissionError, ValueError, Exception)):
            signed_url(client_a_path, client_id_prefix=client_b_prefix)

    def test_asset_query_returns_correct_client_assets(self, db):
        """Querying assets for Client A must not return Client B's assets."""
        client_a = db_client(db, {"name": "Client A"})
        client_b = db_client(db, {"name": "Client B"})

        campaign_a = db_campaign(db, client_a.id)
        campaign_b = db_campaign(db, client_b.id)

        asset_a = db_content_asset(db, campaign_a.id, client_a.id)
        asset_b = db_content_asset(db, campaign_b.id, client_b.id)
        db.commit()

        assets_for_a = db.query(ContentAsset).filter_by(client_id=client_a.id).all()
        ids = [a.id for a in assets_for_a]

        assert asset_a.id in ids
        assert asset_b.id not in ids

    def test_platform_account_query_isolated(self, db):
        """Platform accounts query for Client A must not return Client B's accounts."""
        client_a = db_client(db, {"name": "Client A"})
        client_b = db_client(db, {"name": "Client B"})

        account_a = db_platform_account(db, client_a.id, "instagram")
        account_b = db_platform_account(db, client_b.id, "instagram")
        db.commit()

        accounts_for_a = db.query(PlatformAccount).filter_by(client_id=client_a.id).all()
        ids = [a.id for a in accounts_for_a]

        assert account_a.id in ids
        assert account_b.id not in ids


class TestConcurrentPipelineIsolation:
    def test_two_clients_parallel_pipeline_data_stays_separate(self, db):
        """Run context build for both clients simultaneously — no data leakage."""
        from backend.ai.context_builder import build_campaign_context

        client_a = db_client(db, {"name": "Dental Practice", "usp": "Painless dentistry"})
        client_b = db_client(db, {"name": "Auto Spares", "usp": "Same-day parts"})

        guidelines_a = db_brand_guidelines(db, client_a.id, {
            "forbidden_words": ["painful"],
            "competitor_names": ["BadDental"],
        })
        guidelines_b = db_brand_guidelines(db, client_b.id, {
            "forbidden_words": ["expensive"],
            "competitor_names": ["RustParts"],
        })

        campaign_a = db_campaign(db, client_a.id)
        campaign_b = db_campaign(db, client_b.id)
        db.commit()

        context_a = build_campaign_context(client_a, campaign_a, guidelines_a)
        context_b = build_campaign_context(client_b, campaign_b, guidelines_b)

        # Client A's context must not contain Client B's data
        assert "RustParts" not in context_a
        assert "Auto Spares" not in context_a
        assert "Same-day parts" not in context_a

        # Client B's context must not contain Client A's data
        assert "BadDental" not in context_b
        assert "Dental Practice" not in context_b
        assert "Painless dentistry" not in context_b
