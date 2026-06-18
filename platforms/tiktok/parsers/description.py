"""Parse full post description from TikTok customtdk API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from platforms.tiktok.parsers.item import ParsedItem


@dataclass(slots=True)
class ParsedCustomTdk:
    description: str | None
    description_length: int | None
    keywords: list[str]


def _item_tdk(payload: dict[str, Any]) -> dict[str, Any] | None:
    if int(payload.get("status_code") or payload.get("statusCode") or 0) != 0:
        return None
    tdk = payload.get("itemCustomTDK")
    return tdk if isinstance(tdk, dict) else None


def _parse_keywords(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    keywords: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        keyword = item.strip()
        if keyword:
            keywords.append(keyword)
    return keywords


def parse_customtdk(payload: dict[str, Any]) -> ParsedCustomTdk | None:
    """Parse itemCustomTDK.article and keywords from customtdk API response."""
    tdk = _item_tdk(payload)
    if tdk is None:
        return None

    article = tdk.get("article")
    description = article.strip() if isinstance(article, str) and article.strip() else None
    keywords = _parse_keywords(tdk.get("keywords"))

    if description is None and not keywords:
        return None

    return ParsedCustomTdk(
        description=description,
        description_length=len(description) if description else None,
        keywords=keywords,
    )


def apply_customtdk(item: ParsedItem, payload: dict[str, Any]) -> None:
    parsed = parse_customtdk(payload)
    if parsed is None:
        return
    item.description = parsed.description
    item.description_length = parsed.description_length
    item.description_keywords = parsed.keywords
