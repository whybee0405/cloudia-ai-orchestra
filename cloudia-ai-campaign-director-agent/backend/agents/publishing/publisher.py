"""Publisher Agent — posts to platform via API. Run by Celery Beat at scheduled_for time."""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from backend.agents.base import BaseAgent, AgentError
from backend.db.models import (
    ScheduledPost, ContentAsset, PlatformAccount, Campaign,
    ContentCalendar, PublishedPost
)
from backend.platforms.base import decrypt
from backend.media import storage
from backend.config import get_settings

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    pass


class PublisherAgent(BaseAgent):
    name = "publisher"

    def run(self, scheduled_post_id: int) -> dict:
        post = self.db.get(ScheduledPost, scheduled_post_id)
        if not post:
            raise AgentError(f"ScheduledPost {scheduled_post_id} not found")

        asset = self.db.get(ContentAsset, post.asset_id)
        account = self.db.get(PlatformAccount, post.platform_account_id)
        cal = self.db.get(ContentCalendar, post.calendar_id)
        campaign = self.db.get(Campaign, cal.campaign_id)

        self._start_task(campaign.id, cal.id, {"scheduled_post_id": scheduled_post_id}, pipeline_order=50)

        # Pre-flight checks
        if account.client_id != campaign.client_id:
            msg = f"SECURITY: account.client_id={account.client_id} != campaign.client_id={campaign.client_id}"
            logger.critical(msg)
            self._fail_task(msg)
            raise SecurityError(msg)

        if not account.is_active:
            self._fail_task("Platform account is inactive")
            post.status = "failed"
            self.db.commit()
            raise AgentError("Platform account inactive")

        if account.token_expires_at:
            exp = account.token_expires_at.replace(tzinfo=timezone.utc) if account.token_expires_at.tzinfo is None else account.token_expires_at
            if exp < datetime.now(timezone.utc):
                self._fail_task("Token expired — re-authorise required")
                post.status = "failed"
                self.db.commit()
                raise AgentError("Token expired")

        platform_path = (asset.platform_versions or {}).get(cal.platform, {})
        if isinstance(platform_path, dict):
            media_path = platform_path.get("path") or asset.storage_path
        else:
            media_path = asset.storage_path

        platform_post_id = self._post_to_platform(account, asset, post, cal.platform, media_path, post.caption)

        published = PublishedPost(
            scheduled_post_id=post.id,
            platform=cal.platform,
            platform_post_id=platform_post_id,
            published_at=datetime.now(timezone.utc),
        )
        self.db.add(published)
        post.status = "published"
        cal.status = "published"
        self.db.flush()

        # Queue analytics tasks
        self._queue_analytics(published.id)

        self.db.commit()
        self._complete_task({"platform_post_id": platform_post_id})
        return {"platform_post_id": platform_post_id, "published_post_id": published.id}

    def _post_to_platform(self, account: PlatformAccount, asset: ContentAsset,
                           post: ScheduledPost, platform: str, media_path: str | None,
                           caption: str) -> str:
        from backend.platforms.meta import MetaPlatform
        from backend.platforms.google import GooglePlatform
        from backend.platforms.linkedin import LinkedInPlatform
        from backend.platforms.tiktok import TikTokPlatform
        from backend.platforms.twitter import TwitterPlatform

        settings = get_settings()
        media_url = None
        if media_path:
            media_url = storage.signed_url(media_path, client_id_prefix=str(account.client_id))

        if platform in ("instagram", "facebook", "whatsapp"):
            mp = MetaPlatform()
            if platform == "instagram":
                if asset.asset_type == "video":
                    return mp.publish_instagram_reel(account, media_url, caption)
                return mp.publish_instagram_image(account, media_url, caption)
            if platform == "facebook":
                return mp.publish_facebook_post(account, caption, media_url)
            return mp.publish_whatsapp_broadcast(account, caption)

        if platform == "google_business":
            return GooglePlatform().publish_google_business_post(account, caption, media_url)

        if platform == "youtube":
            media_bytes = storage.download(media_path) if media_path else b""
            return GooglePlatform().publish_youtube_video(account, media_bytes, caption[:100], caption, post.hashtags or [])

        if platform == "linkedin":
            return LinkedInPlatform().publish_linkedin_post(account, caption, media_url)

        if platform == "tiktok":
            media_bytes = storage.download(media_path) if media_path else b""
            return TikTokPlatform().publish_tiktok_video(account, media_bytes, caption, post.hashtags or [])

        if platform == "twitter":
            return TwitterPlatform().publish_tweet(account, caption[:280])

        raise AgentError(f"Unknown platform: {platform}")

    def _queue_analytics(self, published_post_id: int) -> None:
        from backend.tasks.scheduled_tasks import pull_analytics
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        pull_analytics.apply_async(args=[published_post_id, "24h"], eta=now + timedelta(hours=24))
        pull_analytics.apply_async(args=[published_post_id, "72h"], eta=now + timedelta(hours=72))
        pull_analytics.apply_async(args=[published_post_id, "7d"], eta=now + timedelta(days=7))
