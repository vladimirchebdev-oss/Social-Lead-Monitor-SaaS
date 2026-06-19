"""JSON-serializable API payloads from parsed platform data."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from platforms.registry import FetchResult, PLATFORMS, PlatformInfo


def _to_json(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _to_json(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [_to_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_json(item) for key, item in value.items()}
    return value


def platform_public_dict(platform: PlatformInfo) -> dict[str, Any]:
    return {
        "id": platform.id.value,
        "name": platform.name,
        "available": platform.available,
    }


def platforms_public_list() -> list[dict[str, Any]]:
    return [platform_public_dict(p) for p in PLATFORMS]


def fetch_result_dict(result: FetchResult) -> dict[str, Any]:
    return {
        "platform": result.platform.value,
        "url": result.url,
        "item": _to_json(result.parsed.item),
        "comments": _to_json(result.parsed.comments),
        "comment_stats": _to_json(result.stats),
    }
