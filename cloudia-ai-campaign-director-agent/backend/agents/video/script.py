"""Script Agent — video scripts and storyboards."""
from backend.agents.base import BaseAgent, AgentError
from backend.db.models import ContentCalendar, Campaign, Client, BrandGuidelines, ContentAsset
from backend.ai import claude
from backend.ai.context_builder import build_campaign_context
from backend.ai.prompts.video_script import VIDEO_SCRIPT_PROMPT
from backend.config import PLATFORM_SPECS


class ScriptAgent(BaseAgent):
    name = "video_script"

    TARGET_DURATIONS = {"reel": 30, "short_video": 30, "long_video": 90, "story": 15}

    def run(self, calendar_id: int) -> dict:
        cal = self.db.get(ContentCalendar, calendar_id)
        if not cal:
            raise AgentError(f"Calendar item {calendar_id} not found")

        campaign = self.db.get(Campaign, cal.campaign_id)
        client = self.db.get(Client, cal.client_id)
        guidelines = self.db.query(BrandGuidelines).filter_by(client_id=cal.client_id).first()

        self._start_task(campaign.id, calendar_id, {"calendar_id": calendar_id}, pipeline_order=15)
        context = build_campaign_context(client, campaign, guidelines)

        platform_spec = PLATFORM_SPECS.get(cal.platform, {})
        video_spec = platform_spec.get(cal.content_type, platform_spec.get("reel", {}))
        target_secs = self.TARGET_DURATIONS.get(cal.content_type, 30)
        max_secs = video_spec.get("max_seconds", 90)
        target_secs = min(target_secs, max_secs)

        prompt = VIDEO_SCRIPT_PROMPT.format(
            content_type=cal.content_type,
            topic=cal.topic or "brand showcase",
            target_seconds=target_secs,
            platform=cal.platform,
        )

        for attempt in range(2):
            script, inp, out, cost = claude.call_json(system_prompt=context, user_prompt=prompt)
            self._track_tokens(inp, out, cost)

            scenes = script.get("scenes", [])
            total = sum(s.get("duration_sec", 0) for s in scenes)
            declared = script.get("total_duration_sec", 0)

            if total == declared and all(k in s for s in scenes for k in ("duration_sec", "visual", "voiceover")):
                break
            if attempt == 1:
                self._fail_task("Script failed validation: duration mismatch or missing scene fields")
                raise AgentError("Script validation failed")

        asset = ContentAsset(
            campaign_id=campaign.id,
            client_id=cal.client_id,
            asset_type="text",
            content_type="script",
            text_content=str(script),
            platform_versions={"script": script},
            status="draft",
            tokens_used=self._total_tokens,
            cost_usd=round(self._total_cost, 6),
            created_by_agent=self.name,
        )
        self.db.add(asset)
        cal.status = "created"
        self.db.flush()
        cal.asset_id = asset.id
        self.db.commit()

        self._complete_task({"asset_id": asset.id})
        return {"asset_id": asset.id, "calendar_id": calendar_id}
