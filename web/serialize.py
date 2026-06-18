"""Convert parsed platform data to JSON-serializable dicts."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from platforms.registry import FetchResult, PLATFORMS, PlatformInfo
from platforms.tiktok.pipeline import TikTokParsedScrape


def _to_json(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _to_json(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [_to_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_json(item) for key, item in value.items()}
    return value


def platform_info_dict(platform: PlatformInfo) -> dict[str, Any]:
    return {
        "id": platform.id.value,
        "name": platform.name,
        "available": platform.available,
        "host_patterns": list(platform.host_patterns),
    }


def parsed_scrape_dict(parsed: TikTokParsedScrape) -> dict[str, Any]:
    return _to_json(parsed)


def fetch_result_dict(result: FetchResult) -> dict[str, Any]:
    return {
        "platform": result.platform.value,
        "url": result.url,
        "item": _to_json(result.parsed.item),
        "comments": _to_json(result.parsed.comments),
        "comment_stats": _to_json(result.stats),
    }


def platforms_list() -> list[dict[str, Any]]:
    return [platform_info_dict(platform) for platform in PLATFORMS]
