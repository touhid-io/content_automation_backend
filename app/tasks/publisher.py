from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.core.config import get_settings
from app.core.security import decrypt_token
from app.db.supabase import get_supabase_client
from app.schemas.common import PublishDeliveryStatus
from app.services.publish_service import PublishService
from app.utils.db import run_db
from app.utils.datetime import utc_now

logger = logging.getLogger(__name__)


async def _fetch_due_posts() -> list[dict[str, Any]]:
    client = get_supabase_client()
    now_iso = utc_now().isoformat()
    response = await run_db(
        lambda: client.table("posts")
        .select(
            "id,user_id,channel_id,cleaned_article,thumbnail_url,status,facebook_publish_status,telegram_publish_status,schedule_time"
        )
        .eq("status", "Scheduled")
        .lte("schedule_time", now_iso)
        .execute()
    )
    return list(response.data or [])


async def _fetch_user_credentials(user_id: str) -> dict[str, Any] | None:
    client = get_supabase_client()
    response = await run_db(
        lambda: client.table("user_credentials")
        .select("user_id,fb_page_token,telegram_bot_token,telegram_chat_id")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows: list[dict[str, Any]] = list(response.data or [])
    return rows[0] if rows else None


async def _update_post_publish_state(
    post_id: str,
    *,
    status: str | None = None,
    facebook_publish_status: PublishDeliveryStatus | None = None,
    telegram_publish_status: PublishDeliveryStatus | None = None,
) -> None:
    payload: dict[str, str] = {}
    if status is not None:
        payload["status"] = status
    if facebook_publish_status is not None:
        payload["facebook_publish_status"] = facebook_publish_status.value
    if telegram_publish_status is not None:
        payload["telegram_publish_status"] = telegram_publish_status.value
    if not payload:
        return

    client = get_supabase_client()
    await run_db(
        lambda: client.table("posts")
        .update(payload)
        .eq("id", post_id)
        .execute()
    )


async def _notify_admin(message: str) -> None:
    settings = get_settings()
    try:
        await PublishService.send_admin_notification(
            admin_bot_token=settings.telegram_bot_token,
            admin_chat_id=settings.telegram_test_chat_id,
            message=message,
        )
    except Exception as exc:
        logger.exception("Admin notification failed: %s", exc)


async def _process_single_post(post: dict[str, Any], semaphore: asyncio.Semaphore) -> None:
    async with semaphore:
        post_id = str(post["id"])
        user_id = str(post["user_id"])
        cleaned_article = str(post.get("cleaned_article") or "")
        thumbnail_url = str(post.get("thumbnail_url") or "")

        try:
            credentials = await _fetch_user_credentials(user_id)
            if credentials is None:
                logger.warning("Missing user_credentials for user_id=%s", user_id)
                return

            fb_page_token = decrypt_token(credentials.get("fb_page_token"))
            telegram_bot_token = decrypt_token(credentials.get("telegram_bot_token"))
            telegram_chat_id = credentials.get("telegram_chat_id")

            if not fb_page_token:
                logger.warning("Facebook Page token missing for user_id=%s", user_id)
                return

            facebook_result = await PublishService.publish_to_facebook_page(
                fb_page_token=fb_page_token,
                cleaned_article=cleaned_article,
                thumbnail_url=thumbnail_url,
            )

            # Mark overall publish success immediately after Facebook succeeds.
            await _update_post_publish_state(
                post_id,
                status="Published",
                facebook_publish_status=PublishDeliveryStatus.PUBLISHED,
            )

            telegram_state = PublishDeliveryStatus.PENDING
            telegram_detail = "not attempted"
            telegram_message_id: str | None = None

            try:
                telegram_result = await PublishService.publish_to_telegram(
                    telegram_bot_token=telegram_bot_token,
                    telegram_chat_id=telegram_chat_id,
                    cleaned_article=cleaned_article,
                    thumbnail_url=thumbnail_url or None,
                )
                if telegram_result.skipped:
                    telegram_state = PublishDeliveryStatus.SKIPPED
                    telegram_detail = telegram_result.detail or "skipped"
                else:
                    telegram_state = PublishDeliveryStatus.PUBLISHED
                    telegram_detail = "sent"
                    telegram_message_id = telegram_result.platform_id
            except Exception as exc:
                telegram_state = PublishDeliveryStatus.FAILED
                telegram_detail = str(exc)
                logger.exception(
                    "Telegram publish failed after Facebook success for post_id=%s: %s",
                    post_id,
                    exc,
                )

            await _update_post_publish_state(
                post_id,
                telegram_publish_status=telegram_state,
            )

            admin_message = (
                "✅ Post publishing processed\n"
                f"post_id: {post_id}\n"
                f"user_id: {user_id}\n"
                f"facebook_status: Published\n"
                f"facebook_post_id: {facebook_result.platform_id or 'n/a'}\n"
                f"telegram_status: {telegram_state.value}\n"
                f"telegram_detail: {telegram_detail}\n"
                f"telegram_message_id: {telegram_message_id or 'n/a'}"
            )
            await _notify_admin(admin_message)
            logger.info("Post %s processed successfully.", post_id)
        except Exception as exc:
            try:
                await _update_post_publish_state(
                    post_id,
                    facebook_publish_status=PublishDeliveryStatus.FAILED,
                )
            except Exception:
                logger.exception("Failed to mark Facebook publish failure for post_id=%s", post_id)
            logger.exception("Publisher failed for post_id=%s: %s", post_id, exc)


async def run_publisher_job() -> None:
    logger.info("Starting publisher job.")
    posts = await _fetch_due_posts()
    if not posts:
        logger.info("No due scheduled posts found.")
        return
    semaphore = asyncio.Semaphore(5)
    await asyncio.gather(*(_process_single_post(post, semaphore) for post in posts))
    logger.info("Publisher job completed.")
