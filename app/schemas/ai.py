from __future__ import annotations

from pydantic import Field

from app.schemas.common import StrictSchema


class ArticleGenerationRequestSchema(StrictSchema):
    gemini_system_prompt: str = ""
    target_word_count: int = Field(gt=0)
    transcript: str = Field(min_length=1)


class ArticleGenerationResultSchema(StrictSchema):
    article: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
