from __future__ import annotations

from pydantic import Field, HttpUrl

from app.schemas.common import StrictSchema


class YouTubeVideoSchema(StrictSchema):
    video_id: str = Field(min_length=11, max_length=11)
    title: str = Field(min_length=1)
    video_url: HttpUrl
    thumbnail_url: HttpUrl
    published_at: str | None = None


class TranscriptResultSchema(StrictSchema):
    video: YouTubeVideoSchema
    transcript: str = Field(min_length=1)
