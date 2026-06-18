"""Parse TikTok post media URLs (video, cover, photos)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from platforms.tiktok.parsers.extract_helper import unescape_json_url


@dataclass(slots=True)
class ParsedMedia:
    video_cover: str | None = None
    photo_urls: list[str] | None = None


def _first_url(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return unescape_json_url(value.strip())
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                return unescape_json_url(item.strip())
    if isinstance(value, dict):
        for key in ("urlList", "url_list", "urls"):
            found = _first_url(value.get(key))
            if found:
                return found
    return None


def _video_cover(video: dict[str, Any]) -> str | None:
    for key in ("originCover", "cover", "dynamicCover", "reflowCover"):
        url = _first_url(video.get(key))
        if url:
            return url
    zoom = video.get("zoomCover")
    if isinstance(zoom, dict):
        for key in ("960", "720", "480", "240"):
            url = _first_url(zoom.get(key))
            if url:
                return url
    return None


def _photo_urls(item: dict[str, Any]) -> list[str]:
    image_post = item.get("imagePost")
    if not isinstance(image_post, dict):
        return []

    images = image_post.get("images")
    if not isinstance(images, list):
        return []

    urls: list[str] = []
    for entry in images:
        if not isinstance(entry, dict):
            continue
        url = None
        for block_key in ("imageURL", "displayImage", "thumbnail"):
            block = entry.get(block_key)
            if isinstance(block, dict):
                url = _first_url(block)
                if url:
                    break
        if url:
            urls.append(url)
    return urls


def parse_media(item: dict[str, Any]) -> ParsedMedia | None:
    video = item.get("video")
    if not isinstance(video, dict):
        video = None

    photo_urls = _photo_urls(item)
    video_cover = _video_cover(video) if video else None

    if not any([video_cover, photo_urls]):
        return None

    return ParsedMedia(
        video_cover=video_cover,
        photo_urls=photo_urls or None,
    )
