from __future__ import annotations

import uuid

from pydantic import Field

from app.schemas.common import QuotaResetReadSchema, StrictSchema, TimestampReadSchema, UUIDReadSchema


class ConnectedChannelBase(StrictSchema):
    user_id: uuid.UUID
    youtube_channel_id: str = Field(min_length=1)
    daily_quota: int = Field(default=5, ge=0)
    today_processed_count: int = Field(default=0, ge=0)


class ConnectedChannelCreate(ConnectedChannelBase):
    pass


class ConnectedChannelUpdate(StrictSchema):
    youtube_channel_id: str | None = Field(default=None, min_length=1)
    daily_quota: int | None = Field(default=None, ge=0)
    today_processed_count: int | None = Field(default=None, ge=0)


class ConnectedChannelRead(
    ConnectedChannelBase,
    UUIDReadSchema,
    TimestampReadSchema,
    QuotaResetReadSchema,
):
    pass
