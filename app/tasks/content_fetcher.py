from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any

from app.db.supabase import get_supabase_client
from app.schemas.ai import ArticleGenerationRequestSchema
from app.schemas.cleaner import TextCleanerRequestSchema
from app.services.ai_service import AIService
from app.services.text_cleaner_service import TextCleanerService
from app.services.youtube_service import YouTubeService
from app.utils.datetime import utc_now
from app.utils.db import run_db

logger = logging.getLogger(__name__)


async def _fetch_connected_channels() -> list[dict[str, Any]]:
    client = get_supabase_client()
    response = await run_db(
        lambda: client.table("connected_channels")
        .select(
            "id,user_id,youtube_channel_id,daily_quota,today_processed_count,quota_reset_date"
        )
        .execute()
    )
    return list(response.data or [])


async def _fetch_user_credentials(user_id: str) -> dict[str, Any] | None:
    client = get_supabase_client()
    response = await run_db(
        lambda: client.table("user_credentials")
        .select("user_id,gemini_system_prompt,target_word_count")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    rows: list[dict[str, Any]] = list(response.data or [])
    return rows[0] if rows else None


async def _fetch_existing_source_video_ids(channel_id: str) -> set[str]:
    client = get_supabase_client()
    response = await run_db(
        lambda: client.table("posts")
        .select("source_video_id")
        .eq("channel_id", channel_id)
        .execute()
    )
    rows: list[dict[str, Any]] = list(response.data or [])
    return {
        row["source_video_id"]
        for row in rows
        if isinstance(row.get("source_video_id"), str) and row["source_video_id"].strip()
    }


async def _insert_draft_post(
    user_id: str,
    channel_id: str,
    source_video_id: str,
    transcript: str,
    cleaned_article: str,
    thumbnail_url: str,
) -> None:
    client = get_supabase_client()
    await run_db(
        lambda: client.table("posts")
        .insert(
            {
                "user_id": user_id,
                "channel_id": channel_id,
                "source_video_id": source_video_id,
                "original_transcript": transcript,
                "cleaned_article": cleaned_article,
                "thumbnail_url": thumbnail_url,
                "status": "Draft",
                "facebook_publish_status": "Pending",
                "telegram_publish_status": "Pending",
            }
        )
        .execute()
    )


async def _update_channel_counters(
    channel_id: str,
    today_processed_count: int,
    quota_reset_date: date,
) -> None:
    client = get_supabase_client()
    await run_db(
        lambda: client.table("connected_channels")
        .update(
            {
                "today_processed_count": today_processed_count,
                "quota_reset_date": quota_reset_date.isoformat(),
            }
        )
        .eq("id", channel_id)
        .execute()
    )


async def _normalize_channel_quota_state(channel: dict[str, Any]) -> dict[str, Any]:
    today = utc_now().date()
    quota_reset_date_raw = channel.get("quota_reset_date")

    if isinstance(quota_reset_date_raw, str):
        try:
            quota_reset_date = date.fromisoformat(quota_reset_date_raw)
        except ValueError:
            quota_reset_date = today
    else:
        quota_reset_date = today

    if quota_reset_date < today:
        await _update_channel_counters(
            channel_id=str(channel["id"]),
            today_processed_count=0,
            quota_reset_date=today,
        )
        channel["today_processed_count"] = 0
        channel["quota_reset_date"] = today.isoformat()

    return channel


async def _process_single_channel(channel: dict[str, Any], semaphore: asyncio.Semaphore) -> None:
    async with semaphore:
        channel_id = str(channel["id"])
        user_id = str(channel["user_id"])
        youtube_channel_id = str(channel["youtube_channel_id"])
        daily_quota = int(channel.get("daily_quota", 0))

        try:
            channel = await _normalize_channel_quota_state(channel)
            today_processed_count = int(channel.get("today_processed_count", 0))

            if today_processed_count >= daily_quota:
                logger.info("Skipping channel %s due to daily quota.", channel_id)
                return

            credentials = await _fetch_user_credentials(user_id)
            if credentials is None:
                logger.warning("No user_credentials found for user_id=%s", user_id)
                return

            existing_video_ids = await _fetch_existing_source_video_ids(channel_id)
            next_video = await YouTubeService.get_next_unprocessed_video(
                channel_id=youtube_channel_id,
                processed_video_ids=existing_video_ids,
            )
            if next_video is None:
                logger.info("No new video found for YouTube channel %s", youtube_channel_id)
                return

            extraction_result = await YouTubeService.extract_video_package(next_video)
            if extraction_result is None:
                logger.warning("Transcript extraction failed for video %s", next_video.video_id)
                return

            ai_result = await AIService.generate_article(
                ArticleGenerationRequestSchema(
                    gemini_system_prompt=str(credentials.get("gemini_system_prompt") or ""),
                    target_word_count=int(credentials.get("target_word_count") or 800),
                    transcript=extraction_result.transcript,
                )
            )

            cleaned_article = TextCleanerService.clean_text(
                TextCleanerRequestSchema(text=ai_result.article, custom_characters_to_remove="")
            )
            if not cleaned_article.strip():
                logger.warning("Cleaned article is empty for video %s", next_video.video_id)
                return

            await _insert_draft_post(
                user_id=user_id,
                channel_id=channel_id,
                source_video_id=next_video.video_id,
                transcript=extraction_result.transcript,
                cleaned_article=cleaned_article,
                thumbnail_url=str(next_video.thumbnail_url),
            )
            await _update_channel_counters(
                channel_id=channel_id,
                today_processed_count=today_processed_count + 1,
                quota_reset_date=utc_now().date(),
            )
            logger.info(
                "Draft post created successfully for user_id=%s channel_id=%s video_id=%s",
                user_id,
                channel_id,
                next_video.video_id,
            )
        except Exception as exc:
            logger.exception(
                "Content fetcher failed for channel_id=%s user_id=%s: %s",
                channel_id,
                user_id,
                exc,
            )


async def run_content_fetcher_job() -> None:
    logger.info("Starting content fetcher job.")
    channels = await _fetch_connected_channels()
    if not channels:
        logger.info("No connected channels found.")
        return
    semaphore = asyncio.Semaphore(5)
    await asyncio.gather(*(_process_single_channel(channel, semaphore) for channel in channels))
    logger.info("Content fetcher job completed.")
