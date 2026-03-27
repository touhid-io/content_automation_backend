from __future__ import annotations

from typing import Any

import httpx

from app.schemas.publish import PublishResultSchema
from app.utils.exceptions import ApplicationError


class PublishService:
    FACEBOOK_GRAPH_API_BASE: str = "https://graph.facebook.com/v23.0"
    TELEGRAM_CAPTION_LIMIT: int = 1024
    TELEGRAM_MESSAGE_LIMIT: int = 4096

    @staticmethod
    def _build_telegram_caption(cleaned_article: str) -> str:
        text = cleaned_article.strip()
        if len(text) <= PublishService.TELEGRAM_CAPTION_LIMIT:
            return text
        truncated = text[: PublishService.TELEGRAM_CAPTION_LIMIT - 3].rstrip()
        return f"{truncated}..."

    @staticmethod
    def _split_telegram_message(cleaned_article: str) -> list[str]:
        text = cleaned_article.strip()
        if not text:
            return []
        if len(text) <= PublishService.TELEGRAM_MESSAGE_LIMIT:
            return [text]

        chunks: list[str] = []
        remaining = text
        while len(remaining) > PublishService.TELEGRAM_MESSAGE_LIMIT:
            split_at = remaining.rfind("\n\n", 0, PublishService.TELEGRAM_MESSAGE_LIMIT)
            if split_at == -1:
                split_at = remaining.rfind(" ", 0, PublishService.TELEGRAM_MESSAGE_LIMIT)
            if split_at == -1:
                split_at = PublishService.TELEGRAM_MESSAGE_LIMIT
            chunk = remaining[:split_at].strip()
            if chunk:
                chunks.append(chunk)
            remaining = remaining[split_at:].strip()
        if remaining:
            chunks.append(remaining)
        return chunks

    @staticmethod
    async def publish_to_facebook_page(
        fb_page_token: str,
        cleaned_article: str,
        thumbnail_url: str,
    ) -> PublishResultSchema:
        endpoint = f"{PublishService.FACEBOOK_GRAPH_API_BASE}/me/photos"
        payload: dict[str, str] = {
            "url": thumbnail_url,
            "caption": cleaned_article,
            "published": "true",
            "access_token": fb_page_token,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(endpoint, data=payload)
                response.raise_for_status()
                data: dict[str, Any] = response.json()
        except httpx.HTTPError as exc:
            raise ApplicationError(f"Facebook publishing failed: {exc}") from exc

        return PublishResultSchema(
            success=True,
            platform="facebook",
            platform_id=str(data.get("post_id") or data.get("id")) if data else None,
            raw_response=data,
        )

    @staticmethod
    async def publish_to_telegram(
        telegram_bot_token: str | None,
        telegram_chat_id: str | None,
        cleaned_article: str,
        thumbnail_url: str | None = None,
    ) -> PublishResultSchema:
        if not telegram_bot_token:
            return PublishResultSchema(
                success=True,
                skipped=True,
                platform="telegram",
                detail="Telegram bot token not found. Skipping Telegram publishing.",
            )
        if not telegram_chat_id:
            return PublishResultSchema(
                success=True,
                skipped=True,
                platform="telegram",
                detail="Telegram chat_id not found. Skipping Telegram publishing.",
            )

        base_url = f"https://api.telegram.org/bot{telegram_bot_token}"
        caption = PublishService._build_telegram_caption(cleaned_article)
        message_chunks = PublishService._split_telegram_message(cleaned_article)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                send_photo_response: dict[str, Any] | None = None
                if thumbnail_url:
                    photo_response = await client.post(
                        f"{base_url}/sendPhoto",
                        data={
                            "chat_id": telegram_chat_id,
                            "photo": thumbnail_url,
                            "caption": caption,
                        },
                    )
                    photo_response.raise_for_status()
                    send_photo_response = photo_response.json()

                sent_message_ids: list[str] = []
                sent_messages_raw: list[dict[str, Any]] = []
                for chunk in message_chunks:
                    message_response = await client.post(
                        f"{base_url}/sendMessage",
                        data={
                            "chat_id": telegram_chat_id,
                            "text": chunk,
                        },
                    )
                    message_response.raise_for_status()
                    message_data: dict[str, Any] = message_response.json()
                    sent_messages_raw.append(message_data)
                    result_data: Any = message_data.get("result")
                    if isinstance(result_data, dict) and result_data.get("message_id") is not None:
                        sent_message_ids.append(str(result_data["message_id"]))
        except httpx.HTTPError as exc:
            raise ApplicationError(f"Telegram publishing failed: {exc}") from exc

        primary_message_id: str | None = sent_message_ids[0] if sent_message_ids else None
        return PublishResultSchema(
            success=True,
            platform="telegram",
            platform_id=primary_message_id,
            raw_response={
                "photo": send_photo_response,
                "messages": sent_messages_raw,
            },
        )

    @staticmethod
    async def send_admin_notification(
        admin_bot_token: str,
        admin_chat_id: str,
        message: str,
    ) -> PublishResultSchema:
        endpoint = f"https://api.telegram.org/bot{admin_bot_token}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    endpoint,
                    data={"chat_id": admin_chat_id, "text": message},
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()
        except httpx.HTTPError as exc:
            raise ApplicationError(f"Admin Telegram notification failed: {exc}") from exc

        result_data: Any = data.get("result")
        message_id: str | None = None
        if isinstance(result_data, dict) and result_data.get("message_id") is not None:
            message_id = str(result_data["message_id"])

        return PublishResultSchema(
            success=True,
            platform="telegram_admin_notification",
            platform_id=message_id,
            raw_response=data,
        )
