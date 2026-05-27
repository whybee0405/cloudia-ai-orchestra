"""Voiceover Agent — ElevenLabs TTS per scene."""
import logging
import ast
from backend.agents.base import BaseAgent, AgentError
from backend.db.models import ContentAsset, Campaign, BrandGuidelines
from backend.ai import elevenlabs_client
from backend.media import storage

logger = logging.getLogger(__name__)


class VoiceoverAgent(BaseAgent):
    name = "voiceover"

    def run(self, script_asset_id: int) -> dict:
        script_asset = self.db.get(ContentAsset, script_asset_id)
        if not script_asset:
            raise AgentError(f"Script asset {script_asset_id} not found")

        campaign = self.db.get(Campaign, script_asset.campaign_id)
        guidelines = self.db.query(BrandGuidelines).filter_by(client_id=script_asset.client_id).first()
        voice_id = (guidelines.voice_id if guidelines else None) or elevenlabs_client.DEFAULT_VOICE_ID

        self._start_task(campaign.id, None, {"script_asset_id": script_asset_id}, pipeline_order=20)

        script = script_asset.platform_versions.get("script", {}) if script_asset.platform_versions else {}
        if not script:
            try:
                script = ast.literal_eval(script_asset.text_content or "{}")
            except Exception:
                raise AgentError("Cannot parse script from asset")

        scenes = script.get("scenes", [])
        if not scenes:
            raise AgentError("Script has no scenes")

        audio_paths = []
        for i, scene in enumerate(scenes):
            voiceover_text = scene.get("voiceover", "")
            if not voiceover_text:
                continue
            audio_bytes = elevenlabs_client.generate_speech(voiceover_text, voice_id=voice_id)
            filename = f"{script_asset_id}_scene_{i + 1}.mp3"
            obj_path = storage.object_path(script_asset.client_id, campaign.id, "raw", "audio", filename)
            storage.upload(audio_bytes, obj_path, content_type="audio/mpeg")
            audio_paths.append({"scene": i + 1, "path": obj_path})

        audio_asset = ContentAsset(
            campaign_id=campaign.id,
            client_id=script_asset.client_id,
            asset_type="audio",
            content_type="voiceover",
            platform_versions={"scenes": audio_paths, "script_asset_id": script_asset_id},
            status="draft",
            created_by_agent=self.name,
        )
        self.db.add(audio_asset)
        self.db.commit()

        self._complete_task({"audio_asset_id": audio_asset.id, "scene_count": len(audio_paths)})
        return {"audio_asset_id": audio_asset.id, "script_asset_id": script_asset_id}
