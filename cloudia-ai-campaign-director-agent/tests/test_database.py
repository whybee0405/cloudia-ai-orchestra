"""Section 3 — Database integrity tests."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from sqlalchemy.exc import IntegrityError

from backend.db.models import (
    Client, Campaign, ContentCalendar, ContentAsset, AssetVersion,
    BrandGuidelines, PlatformAccount, ScheduledPost, PublishedPost,
    PostAnalytics, AgentTask, ApprovalGate
)
from backend.platforms.base import encrypt, decrypt
from tests.factories import db_client, db_campaign, db_platform_account, db_calendar_item, db_content_asset


# ── 3.1 Schema ─────────────────────────────────────────────────────────────────

class TestSchema:
    def test_all_models_create(self, db):
        client = db_client(db)
        campaign = db_campaign(db, client.id)
        assert client.id is not None
        assert campaign.id is not None

    def test_campaign_client_id_fk_enforced(self, db):
        with pytest.raises(IntegrityError):
            bad = Campaign(client_id=99999, name="Orphan", brief={}, platforms=[])
            db.add(bad)
            db.flush()

    def test_content_calendar_campaign_fk_enforced(self, db):
        client = db_client(db)
        with pytest.raises(IntegrityError):
            item = ContentCalendar(
                campaign_id=99999, client_id=client.id,
                platform="instagram", content_type="image_post",
                scheduled_for=datetime.now(timezone.utc),
            )
            db.add(item)
            db.flush()

    def test_platform_account_unique_constraint(self, db):
        client = db_client(db)
        acc1 = db_platform_account(db, client.id, "instagram")
        with pytest.raises(IntegrityError):
            acc2 = PlatformAccount(
                client_id=client.id,
                platform="instagram",
                account_id=acc1.account_id,
                access_token=encrypt("token2"),
                is_active=True,
            )
            db.add(acc2)
            db.flush()

    def test_published_posts_fk_enforced(self, db):
        with pytest.raises(IntegrityError):
            pub = PublishedPost(
                scheduled_post_id=99999,
                platform="instagram",
                platform_post_id="test",
                published_at=datetime.now(timezone.utc),
            )
            db.add(pub)
            db.flush()

    def test_post_analytics_fk_enforced(self, db):
        with pytest.raises(IntegrityError):
            analytics = PostAnalytics(
                published_post_id=99999,
                snapshot_type="24h",
                pulled_at=datetime.now(timezone.utc),
            )
            db.add(analytics)
            db.flush()


# ── 3.2 Cascade Behaviour ─────────────────────────────────────────────────────

class TestCascades:
    def test_delete_campaign_cascades_to_calendar(self, db):
        client = db_client(db)
        campaign = db_campaign(db, client.id)
        cal = db_calendar_item(db, campaign.id, client.id)
        db.delete(campaign)
        db.commit()
        assert db.get(ContentCalendar, cal.id) is None

    def test_delete_campaign_cascades_to_agent_tasks(self, db):
        client = db_client(db)
        campaign = db_campaign(db, client.id)
        task = AgentTask(campaign_id=campaign.id, agent_name="test", status="running")
        db.add(task)
        db.flush()
        db.delete(campaign)
        db.commit()
        assert db.get(AgentTask, task.id) is None

    def test_delete_campaign_cascades_to_approval_gates(self, db):
        client = db_client(db)
        campaign = db_campaign(db, client.id)
        gate = ApprovalGate(campaign_id=campaign.id, gate_name="calendar_review", status="pending")
        db.add(gate)
        db.flush()
        db.delete(campaign)
        db.commit()
        assert db.get(ApprovalGate, gate.id) is None

    def test_delete_asset_cascades_to_versions(self, db):
        client = db_client(db)
        campaign = db_campaign(db, client.id)
        asset = db_content_asset(db, campaign.id, client.id)
        version = AssetVersion(asset_id=asset.id, version_number=1, storage_path="test/path.jpg")
        db.add(version)
        db.flush()
        db.delete(asset)
        db.commit()
        assert db.get(AssetVersion, version.id) is None

    def test_delete_published_post_cascades_to_analytics(self, db):
        client = db_client(db)
        campaign = db_campaign(db, client.id)
        asset = db_content_asset(db, campaign.id, client.id)
        account = db_platform_account(db, client.id)
        cal = db_calendar_item(db, campaign.id, client.id)
        cal.asset_id = asset.id
        db.flush()

        from tests.factories import db_scheduled_post, db_published_post
        sp = db_scheduled_post(db, cal.id, asset.id, account.id)
        pub = db_published_post(db, sp.id)
        analytics = PostAnalytics(
            published_post_id=pub.id, snapshot_type="24h",
            pulled_at=datetime.now(timezone.utc),
        )
        db.add(analytics)
        db.flush()

        db.delete(pub)
        db.commit()
        assert db.get(PostAnalytics, analytics.id) is None


# ── 3.3 OAuth Token Encryption ────────────────────────────────────────────────

class TestTokenEncryption:
    def test_access_token_stored_encrypted(self, db):
        client = db_client(db)
        raw_token = "EAABwzLixnjYBO1234567890ABCDEF"
        account = db_platform_account(db, client.id, overrides={
            "access_token": raw_token  # factory calls encrypt()
        })
        db.refresh(account)
        assert account.access_token != raw_token
        assert account.access_token.startswith("gAAAAA") or len(account.access_token) > 50

    def test_decrypted_token_matches_original(self, db):
        client = db_client(db)
        # The factory encrypts "test_access_token" (see factories.py make_platform_account default)
        account = db_platform_account(db, client.id)
        stored = account.access_token
        decrypted = decrypt(stored)
        assert decrypted == "test_access_token"

    def test_encryption_key_missing_refuses_start(self):
        """_get_fernet raises RuntimeError when key is empty."""
        import backend.platforms.base as base_module
        original_fernet = base_module._fernet
        try:
            # Force reset the cached instance
            base_module._fernet = None
            with patch("backend.platforms.base.get_settings") as mock_settings:
                mock_settings.return_value.encryption_key = ""
                with pytest.raises((RuntimeError, ValueError)):
                    base_module._get_fernet()
        finally:
            # Restore so other tests keep working
            base_module._fernet = original_fernet

    def test_token_not_in_logs(self, db, caplog):
        import logging
        client = db_client(db)
        account = db_platform_account(db, client.id)
        # Trigger a decrypt
        decrypt(account.access_token)
        # Raw token "test_token" should not appear in any log output
        assert "test_token" not in caplog.text


# ── 3.4 Status Transitions ────────────────────────────────────────────────────

class TestStatusTransitions:
    def test_campaign_valid_status_sequence(self, db):
        client = db_client(db)
        campaign = db_campaign(db, client.id)
        for status in ["planning", "calendar_review", "approved", "active", "completed"]:
            campaign.status = status
            db.commit()
            db.refresh(campaign)
            assert campaign.status == status

    def test_scheduled_post_status_values(self, db):
        client = db_client(db)
        campaign = db_campaign(db, client.id)
        asset = db_content_asset(db, campaign.id, client.id)
        account = db_platform_account(db, client.id)
        cal = db_calendar_item(db, campaign.id, client.id)
        cal.asset_id = asset.id
        db.flush()

        from tests.factories import db_scheduled_post
        post = db_scheduled_post(db, cal.id, asset.id, account.id)
        assert post.status == "queued"
        post.status = "published"
        db.commit()
        assert post.status == "published"
