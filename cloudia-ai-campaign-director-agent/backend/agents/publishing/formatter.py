"""Platform Formatter Agent — creates platform-specific versions of every asset."""
import logging
import os
import tempfile
from backend.agents.base import BaseAgent, AgentError
from backend.db.models import ContentAsset, ContentCalendar, Campaign
from backend.media import storage, image_ops, ffmpeg_ops
from backend.config import PLATFORM_SPECS

logger = logging.getLogger(__name__)


class FormatterAgent(BaseAgent):
    name = "formatter"

    def run(self, asset_id: int) -> dict:
        asset = self.db.get(ContentAsset, asset_id)
        if not asset:
            raise AgentError(f"Asset {asset_id} not found")

        campaign = self.db.get(Campaign, asset.campaign_id)
        self._start_task(campaign.id, None, {"asset_id": asset_id}, pipeline_order=40)

        cal_item = self.db.query(ContentCalendar).filter_by(asset_id=asset_id).first()
        platforms = [cal_item.platform] if cal_item else (campaign.platforms or [])

        platform_versions = asset.platform_versions or {}

        for platform in platforms:
            specs = PLATFORM_SPECS.get(platform, {})

            if asset.asset_type == "image":
                image_spec = specs.get("image_post") or specs.get("story")
                if not image_spec:
                    continue
                raw_bytes = storage.download(asset.storage_path)
                w, h = image_spec["width"], image_spec["height"]
                fmt = image_spec.get("format", "jpg").upper()
                max_mb = image_spec.get("max_mb", 8)
                formatted = image_ops.resize_and_crop(raw_bytes, w, h, fmt)
                if len(formatted) > max_mb * 1024 * 1024:
                    logger.warning("Image exceeds %dMB for %s — compressing", max_mb, platform)
                    formatted = image_ops.resize_and_crop(raw_bytes, w, h, fmt)
                filename = f"{asset_id}_{platform}_fmt.{fmt.lower()}"
                obj_path = storage.object_path(asset.client_id, campaign.id, "edited", "images", filename)
                storage.upload(formatted, obj_path, content_type=f"image/{'jpeg' if fmt == 'JPG' else fmt.lower()}")
                platform_versions[platform] = {"path": obj_path, "width": w, "height": h, "format": fmt.lower()}

            elif asset.asset_type == "video":
                video_spec = specs.get("reel") or specs.get("video") or specs.get("short")
                if not video_spec or video_spec.get("format") != "mp4":
                    continue
                raw_bytes = storage.download(asset.storage_path)
                w, h = video_spec["width"], video_spec["height"]
                max_mb = video_spec.get("max_mb", 650)

                with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_in:
                    tmp_in.write(raw_bytes)
                    tmp_in_path = tmp_in.name
                tmp_out = tmp_in_path + f"_{platform}.mp4"
                try:
                    ffmpeg_ops.transcode(tmp_in_path, tmp_out, w, h, max_mb)
                    with open(tmp_out, "rb") as f:
                        formatted = f.read()
                finally:
                    os.unlink(tmp_in_path)
                    if os.path.exists(tmp_out):
                        os.unlink(tmp_out)

                filename = f"{asset_id}_{platform}_fmt.mp4"
                obj_path = storage.object_path(asset.client_id, campaign.id, "edited", "videos", filename)
                storage.upload(formatted, obj_path, content_type="video/mp4")
                platform_versions[platform] = {"path": obj_path, "width": w, "height": h, "format": "mp4"}

        asset.platform_versions = platform_versions
        asset.status = "approved"
        self.db.commit()

        self._complete_task({"asset_id": asset_id, "platforms_formatted": list(platform_versions.keys())})
        return {"asset_id": asset_id}
