"""B-Roll Agent — Pexels Video API stock footage sourcing per scene."""
import logging
import ast
import httpx
from backend.agents.base import BaseAgent, AgentError
from backend.db.models import ContentAsset, Campaign
from backend.media import storage, ffmpeg_ops
from backend.config import get_settings
import tempfile, os

logger = logging.getLogger(__name__)
PEXELS_VIDEO_SEARCH = "https://api.pexels.com/videos/search"


class BRollAgent(BaseAgent):
    name = "broll"

    def run(self, script_asset_id: int) -> dict:
        script_asset = self.db.get(ContentAsset, script_asset_id)
        if not script_asset:
            raise AgentError(f"Script asset {script_asset_id} not found")

        campaign = self.db.get(Campaign, script_asset.campaign_id)
        settings = get_settings()
        self._start_task(campaign.id, None, {"script_asset_id": script_asset_id}, pipeline_order=20)

        script = script_asset.platform_versions.get("script", {}) if script_asset.platform_versions else {}
        if not script:
            try:
                script = ast.literal_eval(script_asset.text_content or "{}")
            except Exception:
                raise AgentError("Cannot parse script from asset")

        scenes = script.get("scenes", [])
        clip_paths = []

        for i, scene in enumerate(scenes):
            query = scene.get("visual", f"scene {i + 1}")
            duration = scene.get("duration_sec", 5)
            clip_bytes = self._fetch_clip(query, settings.pexels_api_key)

            if not clip_bytes:
                # Fallback: generate a placeholder black frame
                clip_bytes = self._make_placeholder()

            filename = f"{script_asset_id}_scene_{i + 1}_raw.mp4"
            obj_path = storage.object_path(script_asset.client_id, campaign.id, "raw", "videos", filename)
            storage.upload(clip_bytes, obj_path, content_type="video/mp4")

            # Trim clip to scene duration
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_in:
                tmp_in.write(clip_bytes)
                tmp_in_path = tmp_in.name
            tmp_out_path = tmp_in_path.replace("_raw.mp4", "_trimmed.mp4")
            try:
                ffmpeg_ops.trim_clip(tmp_in_path, tmp_out_path, duration)
                trimmed_path = f"{script_asset_id}_scene_{i + 1}_trimmed.mp4"
                obj_trimmed = storage.object_path(script_asset.client_id, campaign.id, "raw", "videos", trimmed_path)
                with open(tmp_out_path, "rb") as f:
                    storage.upload(f.read(), obj_trimmed)
                clip_paths.append({"scene": i + 1, "path": obj_trimmed, "duration_sec": duration})
            finally:
                os.unlink(tmp_in_path)
                if os.path.exists(tmp_out_path):
                    os.unlink(tmp_out_path)

        broll_asset = ContentAsset(
            campaign_id=campaign.id,
            client_id=script_asset.client_id,
            asset_type="video",
            content_type="broll",
            platform_versions={"clips": clip_paths, "script_asset_id": script_asset_id},
            status="draft",
            created_by_agent=self.name,
        )
        self.db.add(broll_asset)
        self.db.commit()

        self._complete_task({"broll_asset_id": broll_asset.id})
        return {"broll_asset_id": broll_asset.id, "script_asset_id": script_asset_id}

    def _fetch_clip(self, query: str, api_key: str) -> bytes | None:
        if not api_key:
            return None
        try:
            r = httpx.get(PEXELS_VIDEO_SEARCH, params={"query": query, "per_page": 1, "orientation": "portrait"},
                          headers={"Authorization": api_key}, timeout=30)
            if r.status_code == 200 and r.json().get("videos"):
                video = r.json()["videos"][0]
                file_url = video["video_files"][0]["link"]
                return httpx.get(file_url, timeout=120, follow_redirects=True).content
        except Exception as exc:
            logger.warning("Pexels video fetch failed: %s", exc)
        return None

    def _make_placeholder(self) -> bytes:
        """Return bytes of a 5-second black video using ffmpeg."""
        import subprocess
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=black:size=1080x1920:rate=30",
            "-t", "5", "-c:v", "libx264", tmp_path
        ], capture_output=True)
        with open(tmp_path, "rb") as f:
            data = f.read()
        os.unlink(tmp_path)
        return data
