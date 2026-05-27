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

    model_config = {"env_file": ".env", "case_sensitive": False}


@lru_cache
def get_settings() -> Settings:
    return Settings()
