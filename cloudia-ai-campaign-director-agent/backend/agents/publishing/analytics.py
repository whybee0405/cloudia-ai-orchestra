"""Analytics Agent — pulls performance data from platforms at 24h, 72h, 7d snapshots."""
import logging
from datetime import datetime, timezone
from decimal import Decimal
import httpx
from sqlalchemy.orm import Session

from backend.agents.base import BaseAgent, AgentError
from backend.db.models import PublishedPost, PostAnalytics, PlatformAccount, ScheduledPost
from backend.platforms.base import decrypt

logger = logging.getLogger(__name__)


class AnalyticsAgent(BaseAgent):
    name = "analytics"

    def run(self, published_post_id: int, snapshot_type: str) -> dict:
        pub = self.db.get(PublishedPost, published_post_id)
        if not pub:
            raise AgentError(f"PublishedPost {published_post_id} not found")

        scheduled_post = self.db.get(ScheduledPost, pub.scheduled_post_id)
        account = self.db.get(PlatformAccount, scheduled_post.platform_account_id)

        if not account or not account.is_active:
            logger.info("Skipping analytics — platform account inactive or missing")
            return {"skipped": True}

        self._start_task(
            scheduled_post.calendar_item.campaign_id if scheduled_post.calendar_item else 0,
            None,
            {"published_post_id": published_post_id, "snapshot_type": snapshot_type},
            pipeline_order=60,
        )

        raw_data = self._fetch_analytics(pub, account)
        stats = self._parse_stats(raw_data, pub.platform)

        reach = stats.get("reach") or 0
        likes = stats.get("likes") or 0
        comments = stats.get("comments") or 0
        shares = stats.get("shares") or 0
        engagement_rate = (
            Decimal(str((likes + comments + shares) / reach)).quantize(Decimal("0.0001"))
            if reach > 0 else None
        )

        record = PostAnalytics(
            published_post_id=published_post_id,
            snapshot_type=snapshot_type,
            pulled_at=datetime.now(timezone.utc),
            impressions=stats.get("impressions"),
            reach=reach or None,
            likes=likes,
            comments=comments,
            shares=shares,
            saves=stats.get("saves"),
            clicks=stats.get("clicks"),
            video_views=stats.get("video_views"),
            engagement_rate=engagement_rate,
            platform_raw=raw_data,
        )
        self.db.add(record)
        self.db.commit()

        if snapshot_type == "7d" and engagement_rate is not None:
            self._flag_performance(published_post_id, float(engagement_rate))

        self._complete_task({"snapshot_type": snapshot_type, "engagement_rate": str(engagement_rate)})
        return {"snapshot_type": snapshot_type, "engagement_rate": str(engagement_rate)}

    def _fetch_analytics(self, pub: PublishedPost, account: PlatformAccount) -> dict:
        """Fetch analytics from the relevant platform API."""
        platform = pub.platform
        token = decrypt(account.access_token) if account.access_token else ""

        try:
            if platform == "instagram":
                return self._fetch_ig_analytics(pub.platform_post_id, token)
            if platform == "facebook":
                return self._fetch_fb_analytics(pub.platform_post_id, token)
            if platform == "linkedin":
                return self._fetch_li_analytics(pub.platform_post_id, token)
        except Exception as exc:
            logger.warning("Analytics fetch failed for %s post %s: %s", platform, pub.platform_post_id, exc)

        return {}

    def _fetch_ig_analytics(self, post_id: str, token: str) -> dict:
        fields = "impressions,reach,likes,comments,shares,saved"
        r = httpx.get(
            f"https://graph.facebook.com/v19.0/{post_id}/insights",
            params={"metric": fields, "access_token": token},
            timeout=30,
        )
        if r.status_code != 200:
            return {}
        data = r.json().get("data", [])
        return {item["name"]: item.get("values", [{}])[0].get("value", 0) for item in data}

    def _fetch_fb_analytics(self, post_id: str, token: str) -> dict:
        r = httpx.get(
            f"https://graph.facebook.com/v19.0/{post_id}",
            params={"fields": "insights.metric(post_impressions,post_reach,post_reactions_by_type_total)", "access_token": token},
            timeout=30,
        )
        return r.json() if r.status_code == 200 else {}

    def _fetch_li_analytics(self, post_id: str, token: str) -> dict:
        r = httpx.get(
            "https://api.linkedin.com/v2/organizationalEntityShareStatistics",
            params={"q": "organizationalEntity", "shares[0]": post_id},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        return r.json() if r.status_code == 200 else {}

    def _parse_stats(self, raw: dict, platform: str) -> dict:
        """Normalise platform-specific response to common fields."""
        if not raw:
            return {}
        stats: dict = {}
        if platform == "instagram":
            stats = {
                "impressions": raw.get("impressions", 0),
                "reach": raw.get("reach", 0),
                "likes": raw.get("likes", 0),
                "comments": raw.get("comments", 0),
                "shares": raw.get("shares", 0),
                "saves": raw.get("saved", 0),
            }
        return stats

    def _flag_performance(self, published_post_id: int, engagement_rate: float) -> None:
        UNDERPERFORM_THRESHOLD = 0.005
        if engagement_rate < UNDERPERFORM_THRESHOLD:
            logger.warning("Underperforming post %d: engagement_rate=%.4f", published_post_id, engagement_rate)
