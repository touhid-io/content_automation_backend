from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="Content Automation Engine", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    app_env: str = Field(default="development", alias="APP_ENV")
    enable_scheduler: bool = Field(default=True, alias="ENABLE_SCHEDULER")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    supabase_url: str = Field(..., alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(..., alias="SUPABASE_SERVICE_ROLE_KEY")

    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY")
    yt_extractor_api_key: str = Field(..., alias="YT_EXTRACTOR_API_KEY")

    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    telegram_test_chat_id: str = Field(..., alias="TELEGRAM_TEST_CHAT_ID")

    facebook_app_id: str = Field(..., alias="FACEBOOK_APP_ID")
    facebook_app_secret: str = Field(..., alias="FACEBOOK_APP_SECRET")
    encryption_secret_key: str = Field(..., alias="ENCRYPTION_SECRET_KEY")


@lru_cache
def get_settings() -> Settings:
    return Settings()
