from __future__ import annotations

import asyncio
import json
import re
import xml.etree.ElementTree as ET
from typing import Any

import httpx
import requests

from app.core.config import get_settings
from app.schemas.youtube import TranscriptResultSchema, YouTubeVideoSchema


# Preserved from the provided snippet, updated to use validated settings.
def extract_transcript(youtube_url):
    settings = get_settings()
    url = "https://yt-transcript-extractor-backend.onrender.com/api/v1/extract-transcript"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": settings.yt_extractor_api_key,
    }
    payload = {"video_url": youtube_url}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        return response.json().get("data")
    except requests.exceptions.RequestException as e:
        print(e)
        return None


class YouTubeService:
    RSS_FEED_URL: str = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

    @staticmethod
    def build_thumbnail_url(video_id: str) -> str:
        return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

    @staticmethod
    def extract_video_id_from_url(youtube_url: str) -> str | None:
        patterns: tuple[str, ...] = (
            r"(?:v=)([A-Za-z0-9_-]{11})",
            r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
            r"(?:embed/)([A-Za-z0-9_-]{11})",
            r"(?:shorts/)([A-Za-z0-9_-]{11})",
        )
        for pattern in patterns:
            match = re.search(pattern, youtube_url)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _normalize_transcript_payload(raw_data: Any) -> str | None:
        if raw_data is None:
            return None
        if isinstance(raw_data, str):
            return raw_data.strip() or None
        if isinstance(raw_data, list):
            text_parts: list[str] = []
            for item in raw_data:
                if isinstance(item, str) and item.strip():
                    text_parts.append(item.strip())
                elif isinstance(item, dict):
                    text_value: Any = item.get("text")
                    if isinstance(text_value, str) and text_value.strip():
                        text_parts.append(text_value.strip())
            joined = " ".join(text_parts).strip()
            return joined or None
        if isinstance(raw_data, dict):
            for key in ("transcript", "text", "content"):
                value: Any = raw_data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return None

    @staticmethod
    async def extract_transcript_async(youtube_url: str) -> str | None:
        raw_data: Any = await asyncio.to_thread(extract_transcript, youtube_url)
        return YouTubeService._normalize_transcript_payload(raw_data)

    @staticmethod
    async def fetch_recent_videos(
        channel_id: str,
        limit: int = 10,
        timeout_seconds: float = 20.0,
    ) -> list[YouTubeVideoSchema]:
        feed_url = YouTubeService.RSS_FEED_URL.format(channel_id=channel_id)
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(feed_url)
            response.raise_for_status()
            xml_text = response.text

        root = ET.fromstring(xml_text)
        namespaces: dict[str, str] = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
        }

        videos: list[YouTubeVideoSchema] = []
        for entry in root.findall("atom:entry", namespaces):
            video_id = entry.findtext("yt:videoId", default=None, namespaces=namespaces)
            title = entry.findtext("atom:title", default=None, namespaces=namespaces)
            published_at = entry.findtext("atom:published", default=None, namespaces=namespaces)
            link_element = entry.find("atom:link", namespaces)
            href = link_element.attrib.get("href") if link_element is not None else None

            if not video_id or not title or not href:
                continue

            videos.append(
                YouTubeVideoSchema(
                    video_id=video_id,
                    title=title,
                    video_url=href,
                    thumbnail_url=YouTubeService.build_thumbnail_url(video_id),
                    published_at=published_at,
                )
            )
            if len(videos) >= limit:
                break
        return videos

    @staticmethod
    async def get_next_unprocessed_video(
        channel_id: str,
        processed_video_ids: set[str],
    ) -> YouTubeVideoSchema | None:
        videos = await YouTubeService.fetch_recent_videos(channel_id=channel_id)
        for video in videos:
            if video.video_id not in processed_video_ids:
                return video
        return None

    @staticmethod
    async def extract_video_package(video: YouTubeVideoSchema) -> TranscriptResultSchema | None:
        transcript = await YouTubeService.extract_transcript_async(str(video.video_url))
        if transcript is None:
            return None
        return TranscriptResultSchema(video=video, transcript=transcript)
