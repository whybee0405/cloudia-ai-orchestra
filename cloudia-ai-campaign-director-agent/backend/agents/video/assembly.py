"""Video Assembly Agent — assembles final video via ffmpeg."""
import logging
import tempfile
import os
from backend.agents.base import BaseAgent, AgentError
from backend.db.models import ContentAsset, Campaign, BrandGuidelines
from backend.media import storage, ffmpeg_ops

logger = logging.getLogger(__name__)


class VideoAssemblyAgent(BaseAgent):
    name = "video_assembly"

    def run(self, script_asset_id: int) -> dict:
        script_asset = self.db.get(ContentAsset, script_asset_id)
        if not script_asset:
            raise AgentError(f"Script asset {script_asset_id} not found")

        campaign = self.db.get(Campaign, script_asset.campaign_id)
        guidelines = self.db.query(BrandGuidelines).filter_by(client_id=script_asset.client_id).first()

        self._start_task(campaign.id, None, {"script_asset_id": script_asset_id}, pipeline_order=30)

        # Find the voiceover and broll assets for this script
        voiceover_asset = (
            self.db.query(ContentAsset)
            .filter_by(campaign_id=campaign.id, content_type="voiceover")
            .filter(ContentAsset.platform_versions["script_asset_id"].astext == str(script_asset_id))
            .first()
        )
        broll_asset = (
            self.db.query(ContentAsset)
            .filter_by(campaign_id=campaign.id, content_type="broll")
            .filter(ContentAsset.platform_versions["script_asset_id"].astext == str(script_asset_id))
            .first()
        )

        if not voiceover_asset or not broll_asset:
            raise AgentError("Voiceover or broll asset not ready for assembly")

        clips = (broll_asset.platform_versions or {}).get("clips", [])
        audio_scenes = (voiceover_asset.platform_versions or {}).get("scenes", [])

        if not clips:
            raise AgentError("No clips available for assembly")

        with tempfile.TemporaryDirectory() as tmpdir:
            scene_videos = []
            for clip in clips:
                scene_num = clip["scene"]
                clip_bytes = storage.download(clip["path"])
                clip_path = os.path.join(tmpdir, f"clip_{scene_num}.mp4")
                with open(clip_path, "wb") as f:
                    f.write(clip_bytes)

                # Find matching audio
                audio_info = next((a for a in audio_scenes if a["scene"] == scene_num), None)
                if audio_info:
                    audio_bytes = storage.download(audio_info["path"])
                    audio_path = os.path.join(tmpdir, f"audio_{scene_num}.mp3")
                    with open(audio_path, "wb") as f:
                        f.write(audio_bytes)
                    merged = os.path.join(tmpdir, f"scene_{scene_num}_merged.mp4")
                    ffmpeg_ops.add_audio(clip_path, audio_path, merged)
                    scene_videos.append(merged)
                else:
                    scene_videos.append(clip_path)

            # Concatenate all scenes
            concat_path = os.path.join(tmpdir, "concat.mp4")
            ffmpeg_ops.concatenate(scene_videos, concat_path)

            # Add background music at 15% volume (if music asset exists)
            final_path = os.path.join(tmpdir, "final.mp4")
            os.rename(concat_path, final_path)

            with open(final_path, "rb") as f:
                video_bytes = f.read()

        filename = f"{script_asset_id}_assembled.mp4"
        obj_path = storage.object_path(script_asset.client_id, campaign.id, "raw", "videos", filename)
        storage.upload(video_bytes, obj_path, content_type="video/mp4")

        asset = ContentAsset(
            campaign_id=campaign.id,
            client_id=script_asset.client_id,
            asset_type="video",
            content_type="reel",
            storage_path=obj_path,
            format="mp4",
            status="draft",
            created_by_agent=self.name,
        )
        self.db.add(asset)
        self.db.commit()

        self._complete_task({"asset_id": asset.id})
        return {"asset_id": asset.id, "script_asset_id": script_asset_id}
