from __future__ import annotations

import re

from app.schemas.cleaner import TextCleanerRequestSchema


class TextCleanerService:
    @staticmethod
    def clean_text(payload: TextCleanerRequestSchema) -> str:
        text = payload.text
        if not text.strip():
            return ""

        text = re.sub(r"\s*,\s*(?=(?:and|এবং)\b)", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*—\s*", ", ", text)
        text = re.sub(r"\s-\s", " ", text)

        removable_chars = "".join(
            char for char in payload.custom_characters_to_remove if char not in {"-", ","}
        )
        if removable_chars:
            text = re.sub(f"[{re.escape(removable_chars)}]", "", text)

        text = re.sub(r"\s+([,.;:!?])", r"\1", text)
        text = re.sub(r"([,.;:!?])(?=[^\s,.;:!?])", r"\1 ", text)
        text = re.sub(r",\s*,+", ", ", text)
        text = re.sub(r"\s{2,}", " ", text)
        return text.strip()
