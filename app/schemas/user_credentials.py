from __future__ import annotations

import uuid

from pydantic import Field

from app.schemas.common import StrictSchema, TimestampReadSchema, UUIDReadSchema


class UserCredentialsBase(StrictSchema):
    user_id: uuid.UUID
    fb_page_token: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    gemini_system_prompt: str = ""
    target_word_count: int = Field(default=800, gt=0)


class UserCredentialsCreate(UserCredentialsBase):
    pass


class UserCredentialsUpdate(StrictSchema):
    fb_page_token: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    gemini_system_prompt: str | None = None
    target_word_count: int | None = Field(default=None, gt=0)


class UserCredentialsRead(UserCredentialsBase, UUIDReadSchema, TimestampReadSchema):
    pass


class UserPublishingCredentials(StrictSchema):
    user_id: uuid.UUID
    fb_page_token: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
