"""Scheduler Agent — determines optimal posting time and creates scheduled_post."""
import logging
from datetime import datetime, timezone, timedelta
import pytz
from sqlalchemy.orm import Session

from backend.agents.base import BaseAgent, AgentError
from backend.db.models import ContentCalendar, ContentAsset, Campaign, PlatformAccount, ScheduledPost
from backend.tasks.scheduled_tasks import publish_post

logger = logging.getLogger(__name__)
SAST = pytz.timezone("Africa/Johannesburg")

OPTIMAL_WINDOWS = {
    "instagram":       [(8, 9), (19, 21)],
    "facebook":        [(10, 15)],
    "tiktok":          [(7, 9), (19, 23)],
    "linkedin":        [(8, 10)],
    "whatsapp":        [(9, 11)],
    "google_business": [(10, 12)],
    "youtube":         [(15, 18)],
    "twitter":         [(9, 10), (12, 13), (17, 18)],
}


class SchedulerAgent(BaseAgent):
    name = "scheduler"

    def run(self, calendar_id: int) -> dict:
        cal = self.db.get(ContentCalendar, calendar_id)
        if not cal:
            raise AgentError(f"Calendar item {calendar_id} not found")
        if not cal.asset_id:
            raise AgentError(f"Calendar item {calendar_id} has no asset")

        asset = self.db.get(ContentAsset, cal.asset_id)
        campaign = self.db.get(Campaign, cal.campaign_id)

        self._start_task(campaign.id, calendar_id, {"calendar_id": calendar_id}, pipeline_order=45)

        account = (
            self.db.query(PlatformAccount)
            .filter_by(client_id=cal.client_id, platform=cal.platform, is_active=True)
            .first()
        )
        if not account:
            self._fail_task(f"No active {cal.platform} account for client {cal.client_id}")
            raise AgentError("No active platform account")

        scheduled_for = self._resolve_time(cal)
        now_utc = datetime.now(timezone.utc)
        if scheduled_for <= now_utc:
            self._fail_task("scheduled_for is in the past")
            raise AgentError("Cannot schedule post in the past")

        caption = (asset.platform_versions or {}).get(cal.platform, {})
        caption_text = caption.get("caption", asset.text_content or "") if isinstance(caption, dict) else ""
        hashtags = caption.get("hashtags", []) if isinstance(caption, dict) else []

        post = ScheduledPost(
            calendar_id=calendar_id,
            asset_id=cal.asset_id,
            platform_account_id=account.id,
            scheduled_for=scheduled_for,
            caption=caption_text,
            hashtags=hashtags,
            status="queued",
        )
        self.db.add(post)
        self.db.flush()

        eta = scheduled_for
        task = publish_post.apply_async(args=[post.id], eta=eta)
        post.celery_task_id = task.id
        cal.status = "scheduled"
        self.db.commit()

        self._complete_task({"scheduled_post_id": post.id, "scheduled_for": scheduled_for.isoformat()})
        return {"scheduled_post_id": post.id}

    def _resolve_time(self, cal: ContentCalendar) -> datetime:
        """Use calendar's scheduled_for if set; else pick next optimal window in SAST."""
        now_sast = datetime.now(SAST)
        scheduled = cal.scheduled_for
        if scheduled and scheduled.tzinfo is None:
            scheduled = scheduled.replace(tzinfo=timezone.utc)
        if scheduled and scheduled > datetime.now(timezone.utc):
            return scheduled.astimezone(timezone.utc)

        windows = OPTIMAL_WINDOWS.get(cal.platform, [(9, 18)])
        for days_ahead in range(7):
            candidate = now_sast + timedelta(days=days_ahead)
            for start_h, end_h in windows:
                t = candidate.replace(hour=start_h, minute=0, second=0, microsecond=0)
                if t > now_sast + timedelta(hours=1):
                    return t.astimezone(timezone.utc)
        return (now_sast + timedelta(hours=1)).astimezone(timezone.utc)
