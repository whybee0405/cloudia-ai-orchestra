"""Image Editor Agent — brand overlays, resize to all target platform specs."""
import logging
from sqlalchemy.orm import Session

from backend.agents.base import BaseAgent, AgentError
from backend.db.models import ContentAsset, Campaign, BrandGuidelines
from backend.media import storage, image_ops
from backend.config import PLATFORM_SPECS

logger = logging.getLogger(__name__)


class ImageEditorAgent(BaseAgent):
    name = "image_editor"

    def run(self, asset_id: int) -> dict:
        asset = self.db.get(ContentAsset, asset_id)
        if not asset:
            raise AgentError(f"Asset {asset_id} not found")

        campaign = self.db.get(Campaign, asset.campaign_id)
        guidelines = self.db.query(BrandGuidelines).filter_by(client_id=asset.client_id).first()

        self._start_task(campaign.id, None, {"asset_id": asset_id}, pipeline_order=20)

        image_bytes = storage.download(asset.storage_path)

        # Apply logo overlay if required
        if guidelines and guidelines.required_elements and guidelines.required_elements.get("logo_on_all_images"):
            if guidelines.logo_path:
                try:
                    logo_bytes = storage.download(guidelines.logo_path)
                    image_bytes = image_ops.overlay_logo(image_bytes, logo_bytes)
                except Exception as exc:
                    logger.warning("Logo overlay failed: %s", exc)

        # Apply brand colour banner with CTA if required
        if guidelines and guidelines.required_elements and guidelines.required_elements.get("cta_required"):
            primary_colour = guidelines.primary_colour or "#000000"
            image_bytes = image_ops.add_colour_banner(image_bytes, "Learn More →", bg_colour=primary_colour)

        # Resize for each target platform
        platforms: list[str] = campaign.platforms or []
        platform_versions: dict = {}

        for platform in platforms:
            specs = PLATFORM_SPECS.get(platform, {})
            image_spec = specs.get("image_post")
            if not image_spec:
                continue
            w, h = image_spec["width"], image_spec["height"]
            fmt = image_spec.get("format", "jpg").upper()
            resized = image_ops.resize_and_crop(image_bytes, w, h, fmt)

            filename = f"{asset_id}_{platform}.{fmt.lower()}"
            obj_path = storage.object_path(asset.client_id, campaign.id, "edited", "images", filename)
            storage.upload(resized, obj_path, content_type=f"image/{'jpeg' if fmt == 'JPG' else fmt.lower()}")
            platform_versions[platform] = {"path": obj_path, "width": w, "height": h, "format": fmt.lower()}

        asset.platform_versions = platform_versions
        asset.status = "editing"
        self.db.commit()

        self._complete_task({"asset_id": asset_id, "platform_versions": list(platform_versions.keys())})
        return {"asset_id": asset_id}
