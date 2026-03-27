from __future__ import annotations

from pydantic import Field

from app.schemas.common import StrictSchema


class TextCleanerRequestSchema(StrictSchema):
    text: str = Field(default="")
    custom_characters_to_remove: str = Field(default="")
