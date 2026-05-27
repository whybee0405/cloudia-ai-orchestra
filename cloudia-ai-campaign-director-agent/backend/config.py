from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str
    db_password: str = ""

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_root_user: str = ""
    minio_root_password: str = ""
    minio_bucket: str = "cloudia-media"
    minio_secure: bool = False

    # AI APIs
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    openai_api_key: str = ""
    replicate_api_token: str = ""
    elevenlabs_api_key: str = ""

    # Media APIs
    unsplash_access_key: str = ""
    pexels_api_key: str = ""
    canva_api_key: str = ""

    # Meta
    meta_app_id: str = ""
    meta_app_secret: str = ""

    # LinkedIn
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""

    # TikTok
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""

    # Twitter
    twitter_client_id: str = ""
    twitter_client_secret: str = ""

    # Google
    google_client_id: str = ""
    google_client_secret: str = ""

    # App
    oauth_callback_base_url: str = "https://your-domain.com/api"
    secret_key: str = ""
    encryption_key: str = ""
    environment: str = "development"
    allowed_origins: str = "http://localhost:5174"

    # Email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    notification_from: str = ""

    # Celery
    celery_timezone: str = "Africa/Johannesburg"

    # Cost alerts
    claude_spend_alert_zar: float = 200.0
    dalle_spend_alert_usd: float = 5.0

    model_config = {"env_file": ".env", "case_sensitive": False}


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Platform content specifications — used by Formatter Agent and validators
PLATFORM_SPECS = {
    "instagram": {
        "image_post":  {"width": 1080, "height": 1080, "format": "jpg", "max_mb": 8},
        "portrait":    {"width": 1080, "height": 1350, "format": "jpg", "max_mb": 8},
        "landscape":   {"width": 1080, "height": 566,  "format": "jpg", "max_mb": 8},
        "story":       {"width": 1080, "height": 1920, "format": "jpg", "max_mb": 30},
        "reel":        {"width": 1080, "height": 1920, "format": "mp4",
                        "max_mb": 650, "max_seconds": 90, "min_seconds": 3},
        "carousel":    {"width": 1080, "height": 1080, "format": "jpg", "max_slides": 10},
        "caption_max_chars": 2200,
        "hashtag_max": 30,
    },
    "facebook": {
        "image_post":  {"width": 1200, "height": 630, "format": "jpg", "max_mb": 8},
        "story":       {"width": 1080, "height": 1920, "format": "jpg", "max_mb": 30},
        "reel":        {"width": 1080, "height": 1920, "format": "mp4",
                        "max_mb": 1000, "max_seconds": 90},
        "video":       {"width": 1280, "height": 720, "format": "mp4",
                        "max_mb": 10240, "max_seconds": 14400},
        "caption_max_chars": 63206,
    },
    "tiktok": {
        "video":       {"width": 1080, "height": 1920, "format": "mp4",
                        "max_mb": 287, "min_seconds": 3, "max_seconds": 600},
        "caption_max_chars": 2200,
        "hashtag_max": 5,
    },
    "linkedin": {
        "image_post":  {"width": 1200, "height": 627, "format": "jpg", "max_mb": 5},
        "video":       {"width": 1920, "height": 1080, "format": "mp4",
                        "max_mb": 5120, "max_seconds": 600},
        "caption_max_chars": 3000,
    },
    "twitter": {
        "image_post":  {"width": 1600, "height": 900, "format": "jpg", "max_mb": 5},
        "video":       {"width": 1280, "height": 720, "format": "mp4",
                        "max_mb": 512, "max_seconds": 140},
        "caption_max_chars": 280,
    },
    "youtube": {
        "video":       {"width": 1920, "height": 1080, "format": "mp4",
                        "max_mb": 256000, "max_seconds": 43200},
        "short":       {"width": 1080, "height": 1920, "format": "mp4",
                        "max_mb": 256000, "max_seconds": 60},
        "thumbnail":   {"width": 1280, "height": 720, "format": "jpg", "max_mb": 2},
        "description_max_chars": 5000,
    },
    "google_business": {
        "image_post":  {"width": 720, "height": 540, "format": "jpg",
                        "min_width": 400, "min_height": 300, "max_mb": 5},
        "caption_max_chars": 1500,
    },
    "whatsapp": {
        "image":       {"format": "jpg", "max_mb": 5},
        "video":       {"format": "mp4", "max_mb": 64, "max_seconds": 90},
        "message_max_chars": 4096,
    },
}

SUPPORTED_PLATFORMS = list(PLATFORM_SPECS.keys())
