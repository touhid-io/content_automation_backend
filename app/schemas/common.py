from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class StrictSchema(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", from_attributes=True)


class UUIDReadSchema(StrictSchema):
    id: uuid.UUID


class TimestampReadSchema(StrictSchema):
    created_at: datetime
    updated_at: datetime


class QuotaResetReadSchema(StrictSchema):
    quota_reset_date: date


class PostStatus(str, enum.Enum):
    DRAFT = "Draft"
    SCHEDULED = "Scheduled"
    PUBLISHED = "Published"


class PublishDeliveryStatus(str, enum.Enum):
    PENDING = "Pending"
    PUBLISHED = "Published"
    FAILED = "Failed"
    SKIPPED = "Skipped"
