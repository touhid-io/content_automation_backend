from __future__ import annotations

from typing import Any

from pydantic import Field, HttpUrl

from app.schemas.common import StrictSchema


class FacebookPublishInputSchema(StrictSchema):
    fb_page_token: str = Field(min_length=1)
    cleaned_article: str = Field(min_length=1)
    thumbnail_url: HttpUrl


class TelegramPublishInputSchema(StrictSchema):
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    cleaned_article: str = Field(min_length=1)
    thumbnail_url: HttpUrl | None = None


class PublishResultSchema(StrictSchema):
    success: bool
    platform: str = Field(min_length=1)
    platform_id: str | None = None
    skipped: bool = False
    detail: str | None = None
    raw_response: dict[str, Any] | None = None
