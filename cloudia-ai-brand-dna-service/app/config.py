from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    internal_api_secret: str = ""

    campaigns_service_url: str = "http://localhost:8001"
    ads_service_url: str = "http://localhost:8002"
    webdev_service_url: str = "http://localhost:8003"

    port: int = 8000
    environment: str = "development"
    allowed_origins: str = "http://localhost:3000"

    minio_endpoint: str = "minio:9000"
    minio_root_user: str = ""
    minio_root_password: str = ""
    minio_bucket: str = "cloudia-brand-assets"
    minio_secure: bool = False

    model_config = {"env_file": ".env", "case_sensitive": False}


@lru_cache
def get_settings() -> Settings:
    return Settings()
