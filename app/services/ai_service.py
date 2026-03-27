from __future__ import annotations

from typing import ClassVar

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.schemas.ai import ArticleGenerationRequestSchema, ArticleGenerationResultSchema
from app.utils.exceptions import ApplicationError


class AIService:
    MODEL_NAME: str = "gemini-3.1-pro-preview"
    _client: ClassVar[genai.Client | None] = None

    @classmethod
    def _get_client(cls) -> genai.Client:
        if cls._client is None:
            settings = get_settings()
            cls._client = genai.Client(api_key=settings.gemini_api_key)
        return cls._client

    @staticmethod
    def _build_system_prompt(gemini_system_prompt: str, target_word_count: int) -> str:
        base_prompt = gemini_system_prompt.strip()
        dynamic_constraint = (
            f"Strictly write the article in approximately {target_word_count} words."
        )
        instructions: list[str] = [
            base_prompt if base_prompt else "You are an expert content writer.",
            dynamic_constraint,
            "Return only the final article.",
            "Do not include markdown code fences.",
            "Do not add meta-commentary.",
        ]
        return "\n\n".join(instructions)

    @classmethod
    async def generate_article(
        cls,
        payload: ArticleGenerationRequestSchema,
    ) -> ArticleGenerationResultSchema:
        client = cls._get_client()

        system_prompt = cls._build_system_prompt(
            gemini_system_prompt=payload.gemini_system_prompt,
            target_word_count=payload.target_word_count,
        )
        user_prompt = (
            "Transform the following transcript into a polished article.\n\n"
            f"Transcript:\n{payload.transcript}"
        )

        response = await client.aio.models.generate_content(
            model=cls.MODEL_NAME,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
            ),
        )

        article_text = getattr(response, "text", None)
        if not article_text or not article_text.strip():
            raise ApplicationError("Gemini returned an empty article.")

        return ArticleGenerationResultSchema(
            article=article_text.strip(),
            model_name=cls.MODEL_NAME,
        )
