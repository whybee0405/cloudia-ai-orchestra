"""ElevenLabs TTS wrapper."""
import logging
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from typing import Optional

from backend.config import get_settings

logger = logging.getLogger(__name__)
_client: Optional[ElevenLabs] = None

DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel — neutral, clear


def get_client() -> ElevenLabs:
    global _client
    if _client is None:
        _client = ElevenLabs(api_key=get_settings().elevenlabs_api_key)
    return _client


def generate_speech(
    text: str,
    voice_id: str = DEFAULT_VOICE_ID,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    model_id: str = "eleven_multilingual_v2",
) -> bytes:
    """Convert text to speech. Returns raw MP3 bytes."""
    client = get_client()
    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id=model_id,
        voice_settings=VoiceSettings(
            stability=stability,
            similarity_boost=similarity_boost,
        ),
    )
    audio_bytes = b"".join(audio)
    logger.debug("ElevenLabs TTS: %d chars → %d bytes audio", len(text), len(audio_bytes))
    return audio_bytes
