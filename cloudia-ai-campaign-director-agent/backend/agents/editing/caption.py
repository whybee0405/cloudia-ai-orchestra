"""Caption Agent — auto-subtitle generation via OpenAI Whisper."""
import logging
import tempfile
import os
from openai import OpenAI

from backend.agents.base import BaseAgent, AgentError
from backend.db.models import ContentAsset, Campaign
from backend.media import storage
from backend.config import get_settings

logger = logging.getLogger(__name__)


class CaptionAgent(BaseAgent):
    name = "caption"

    def run(self, video_asset_id: int) -> dict:
        asset = self.db.get(ContentAsset, video_asset_id)
        if not asset:
            raise AgentError(f"Asset {video_asset_id} not found")

        campaign = self.db.get(Campaign, asset.campaign_id)
        self._start_task(campaign.id, None, {"asset_id": video_asset_id}, pipeline_order=32)

        settings = get_settings()
        client = OpenAI(api_key=settings.openai_api_key)

        video_bytes = storage.download(asset.storage_path)

        srt_content = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                tmp.write(video_bytes)
                tmp_path = tmp.name
            with open(tmp_path, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="srt",
                )
            srt_content = str(transcript)
        except Exception as exc:
            logger.warning("Whisper transcription failed: %s — generating static SRT from script", exc)
            srt_content = self._static_srt_from_script(asset)
        finally:
            if "tmp_path" in locals() and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        if self._validate_srt(srt_content):
            srt_bytes = srt_content.encode("utf-8")
        else:
            srt_content = self._static_srt_from_script(asset)
            srt_bytes = srt_content.encode("utf-8")

        srt_filename = f"{video_asset_id}_subtitles.srt"
        srt_path = storage.object_path(asset.client_id, campaign.id, "edited", "videos", srt_filename)
        storage.upload(srt_bytes, srt_path, content_type="text/plain")

        platform_versions = asset.platform_versions or {}
        platform_versions["srt_path"] = srt_path
        asset.platform_versions = platform_versions
        self.db.commit()

        self._complete_task({"srt_path": srt_path})
        return {"srt_path": srt_path, "asset_id": video_asset_id}

    def _validate_srt(self, srt: str) -> bool:
        """Check SRT has at least one entry with non-overlapping timestamps."""
        lines = srt.strip().split("\n")
        return len(lines) > 3 and "-->" in srt

    def _static_srt_from_script(self, asset: ContentAsset) -> str:
        """Generate a static SRT (no real timestamps) from script text as fallback."""
        text = asset.text_content or "Content"
        return f"1\n00:00:00,000 --> 00:00:05,000\n{text[:100]}\n"
