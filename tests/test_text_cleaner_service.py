from app.schemas.cleaner import TextCleanerRequestSchema
from app.services.text_cleaner_service import TextCleanerService


def test_clean_text_basic_rules() -> None:
    cleaned = TextCleanerService.clean_text(
        TextCleanerRequestSchema(
            text="Hello , and world — nice - day !",
            custom_characters_to_remove="@#",
        )
    )
    assert cleaned == "Hello and world, nice day!"
