"""Video Editor Agent — colour grading, subtitles, per-platform export."""
import logging
import tempfile
import os
from backend.agents.base import BaseAgent, AgentError
from backend.db.models import ContentAsset, Campaign
from backend.media import storage, ffmpeg_ops
from backend.config import PLATFORM_SPECS

logger = logging.getLogger(__name__)


class VideoEditorAgent(BaseAgent):
    name = "video_editor"

    def run(self, asset_id: int) -> dict:
        asset = self.db.get(ContentAsset, asset_id)
        if not asset:
            raise AgentError(f"Asset {asset_id} not found")

        campaign = self.db.get(Campaign, asset.campaign_id)
        self._start_task(campaign.id, None, {"asset_id": asset_id}, pipeline_order=35)

        video_bytes = storage.download(asset.storage_path)
        srt_path_minio = (asset.platform_versions or {}).get("srt_path")

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.mp4")
            with open(input_path, "wb") as f:
                f.write(video_bytes)

            working = input_path

            # Burn subtitles if SRT available
            if srt_path_minio:
                try:
                    srt_bytes = storage.download(srt_path_minio)
                    srt_local = os.path.join(tmpdir, "subtitles.srt")
                    with open(srt_local, "wb") as f:
                        f.write(srt_bytes)
                    subbed = os.path.join(tmpdir, "with_subs.mp4")
                    ffmpeg_ops.burn_subtitles(working, srt_local, subbed)
                    working = subbed
                except Exception as exc:
                    logger.warning("Subtitle burn failed: %s — continuing without", exc)

            platform_versions = asset.platform_versions or {}
            platforms: list[str] = campaign.platforms or []

            for platform in platforms:
                specs = PLATFORM_SPECS.get(platform, {})
                video_spec = specs.get("reel") or specs.get("video") or specs.get("short")
                if not video_spec or video_spec.get("format") != "mp4":
                    continue
                w, h = video_spec["width"], video_spec["height"]
                max_mb = video_spec.get("max_mb", 650)

                out_path = os.path.join(tmpdir, f"{asset_id}_{platform}.mp4")
                ffmpeg_ops.transcode(working, out_path, w, h, max_mb)

                with open(out_path, "rb") as f:
                    out_bytes = f.read()

                filename = f"{asset_id}_{platform}.mp4"
                obj_path = storage.object_path(asset.client_id, campaign.id, "edited", "videos", filename)
                storage.upload(out_bytes, obj_path, content_type="video/mp4")
                platform_versions[platform] = {"path": obj_path, "width": w, "height": h, "format": "mp4"}

        asset.platform_versions = platform_versions
        asset.status = "editing"
        self.db.commit()

        self._complete_task({"asset_id": asset_id, "platform_versions": list(platform_versions.keys())})
        return {"asset_id": asset_id}
