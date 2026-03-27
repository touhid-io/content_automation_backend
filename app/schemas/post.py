from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field, HttpUrl

from app.schemas.common import (
    PostStatus,
    PublishDeliveryStatus,
    StrictSchema,
    TimestampReadSchema,
    UUIDReadSchema,
)


class PostBase(StrictSchema):
    user_id: uuid.UUID
    channel_id: uuid.UUID
    source_video_id: str | None = None
    original_transcript: str | None = None
    cleaned_article: str | None = None
    thumbnail_url: HttpUrl | None = None
    status: PostStatus = PostStatus.DRAFT
    facebook_publish_status: PublishDeliveryStatus = PublishDeliveryStatus.PENDING
    telegram_publish_status: PublishDeliveryStatus = PublishDeliveryStatus.PENDING
    schedule_time: datetime | None = None


class PostCreate(PostBase):
    pass


class PostUpdate(StrictSchema):
    source_video_id: str | None = None
    original_transcript: str | None = None
    cleaned_article: str | None = None
    thumbnail_url: HttpUrl | None = None
    status: PostStatus | None = None
    facebook_publish_status: PublishDeliveryStatus | None = None
    telegram_publish_status: PublishDeliveryStatus | None = None
    schedule_time: datetime | None = None


class PostRead(PostBase, UUIDReadSchema, TimestampReadSchema):
    pass


class DraftPostPackageCreate(StrictSchema):
    user_id: uuid.UUID
    channel_id: uuid.UUID
    source_video_id: str = Field(min_length=11, max_length=11)
    original_transcript: str = Field(min_length=1)
    cleaned_article: str = Field(min_length=1)
    thumbnail_url: HttpUrl
    status: PostStatus = PostStatus.DRAFT
    facebook_publish_status: PublishDeliveryStatus = PublishDeliveryStatus.PENDING
    telegram_publish_status: PublishDeliveryStatus = PublishDeliveryStatus.PENDING


class ScheduledPostDue(StrictSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    channel_id: uuid.UUID
    cleaned_article: str
    thumbnail_url: HttpUrl | None = None
    status: PostStatus
    facebook_publish_status: PublishDeliveryStatus
    telegram_publish_status: PublishDeliveryStatus
    schedule_time: datetime
