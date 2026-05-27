"""Content Planner Agent — builds the full content calendar from the campaign brief."""
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from backend.agents.base import BaseAgent, AgentError
from backend.db.models import Campaign, Client, BrandGuidelines, ContentCalendar, ApprovalGate
from backend.ai import claude
from backend.ai.context_builder import build_campaign_context
from backend.ai.prompts.planner import CALENDAR_GENERATION_PROMPT
from backend.config import PLATFORM_SPECS

logger = logging.getLogger(__name__)

OPTIMAL_HOURS: dict[str, list[int]] = {
    "instagram":       [8, 19, 20],
    "facebook":        [10, 11, 12, 13, 14],
    "tiktok":          [7, 8, 19, 20, 21, 22],
    "linkedin":        [8, 9, 10],
    "whatsapp":        [9, 10, 11],
    "google_business": [10, 11, 12],
    "youtube":         [15, 16, 17],
    "twitter":         [9, 12, 17],
}


class PlannerAgent(BaseAgent):
    name = "planner"

    def run(self, campaign_id: int) -> dict:
        campaign = self.db.get(Campaign, campaign_id)
        if not campaign:
            raise AgentError(f"Campaign {campaign_id} not found")

        client = self.db.get(Client, campaign.client_id)
        guidelines = self.db.query(BrandGuidelines).filter_by(client_id=campaign.client_id).first()

        task = self._start_task(campaign_id, None, {"campaign_id": campaign_id}, pipeline_order=1)

        context = build_campaign_context(client, campaign, guidelines)
        user_prompt = CALENDAR_GENERATION_PROMPT + f"\n\nCampaign duration: {campaign.duration_days} days\nPosts per week: {campaign.posts_per_week}\nContent mix: {campaign.content_mix}\nPlatforms: {campaign.platforms}"

        calendar_json, inp, out, cost = claude.call_json(
            system_prompt=context,
            user_prompt=user_prompt,
            max_tokens=8192,
        )
        self._track_tokens(inp, out, cost)

        # Validate and clean Claude output
        if not isinstance(calendar_json, list):
            self._fail_task("Planner returned non-list calendar")
            raise AgentError("Planner malformed output")

        calendar_items = self._validate_and_create_calendar(campaign, calendar_json)

        # Create calendar_review approval gate
        gate = ApprovalGate(
            campaign_id=campaign_id,
            gate_name="calendar_review",
            pipeline_order=2,
            status="pending",
        )
        self.db.add(gate)
        campaign.status = "calendar_review"
        self.db.commit()

        self._complete_task({"calendar_items_created": len(calendar_items), "gate_id": gate.id})
        return {"campaign_id": campaign_id, "calendar_count": len(calendar_items), "gate_id": gate.id}

    def _validate_and_create_calendar(self, campaign: Campaign, items: list[dict]) -> list[ContentCalendar]:
        """Clean Claude output, deduplicate, and write content_calendar rows."""
        start = campaign.start_date or datetime.now(timezone.utc).date()
        seen_slots: set[tuple] = set()
        created = []

        for item in items:
            platform = item.get("platform", "").lower()
            content_type = item.get("content_type", "image_post")
            day_offset = int(item.get("day_offset", 0))
            hour = int(item.get("hour", OPTIMAL_HOURS.get(platform, [10])[0]))

            # Reject unknown platforms or content types
            if platform not in PLATFORM_SPECS:
                logger.warning("Skipping unknown platform %r in planner output", platform)
                continue

            valid_types = set(PLATFORM_SPECS[platform].keys()) - {"caption_max_chars", "hashtag_max", "description_max_chars", "message_max_chars"}
            if content_type not in valid_types:
                content_type = "image_post" if "image_post" in valid_types else list(valid_types)[0]

            scheduled_dt = datetime.combine(
                start + timedelta(days=day_offset),
                datetime.min.time().replace(hour=min(hour, 23)),
            )

            # No two posts on same platform within 3 hours
            slot_key = (platform, scheduled_dt.date(), scheduled_dt.hour // 3)
            while slot_key in seen_slots:
                scheduled_dt += timedelta(hours=3)
                slot_key = (platform, scheduled_dt.date(), scheduled_dt.hour // 3)
            seen_slots.add(slot_key)

            cal_item = ContentCalendar(
                campaign_id=campaign.id,
                client_id=campaign.client_id,
                platform=platform,
                content_type=content_type,
                scheduled_for=scheduled_dt,
                topic=item.get("topic", ""),
                status="planned",
            )
            self.db.add(cal_item)
            created.append(cal_item)

        self.db.commit()
        return created
