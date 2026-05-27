"""Graphic Design Agent — Canva API branded templates. Falls back to ImageGeneratorAgent."""
import logging
from sqlalchemy.orm import Session

from backend.agents.base import BaseAgent, AgentError
from backend.db.models import ContentCalendar, Campaign, BrandGuidelines
from backend.config import get_settings

logger = logging.getLogger(__name__)


class GraphicDesignAgent(BaseAgent):
    name = "graphic_design"

    def run(self, calendar_id: int) -> dict:
        settings = get_settings()
        if not settings.canva_api_key:
            logger.info("Canva API key not set — falling back to ImageGeneratorAgent")
            from backend.agents.image.generator import ImageGeneratorAgent
            return ImageGeneratorAgent(self.db).run(calendar_id)

        # Canva API integration goes here when API access is available
        raise AgentError("Canva API integration not yet implemented — set CANVA_API_KEY to enable")
