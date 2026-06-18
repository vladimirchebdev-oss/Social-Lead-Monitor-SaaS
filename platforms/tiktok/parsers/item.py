"""Unified TikTok item parser (video + photo)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from platforms.tiktok.parsers.author import ParsedAuthor, parse_author
from platforms.tiktok.parsers.content import get_content_type
from platforms.tiktok.parsers.extract_helper import get_field, get_list
from platforms.tiktok.parsers.hashtags import ParsedHashtag, parse_hashtags
from platforms.tiktok.parsers.metrics import parse_metrics
from platforms.tiktok.parsers.music import ParsedMusic, parse_music
from platforms.tiktok.parsers.types import PostMetrics


@dataclass(slots=True)
class ParsedItem:
    post_id: str
    content_type: str
    description_preview: str | None
    location_created: str | None
    diversification_labels: list[str]
    metrics: PostMetrics
    author: ParsedAuthor
    hashtags: list[ParsedHashtag]
    music: ParsedMusic | None = None
    description: str | None = None
    description_length: int | None = None
    description_keywords: list[str] | None = None


def parse_item(item: dict[str, Any]) -> ParsedItem | None:
    post_id_raw = get_field(item, "id", path="itemStruct.id")
    if not post_id_raw:
        return None

    metrics = parse_metrics(item)
    author = parse_author(item)
    if metrics is None or author is None:
        return None

    description_preview = get_field(item, "desc", path="itemStruct.desc", optional=True)
    location_created = get_field(item, "locationCreated", path="itemStruct.locationCreated", optional=True)

    labels_raw = get_list(item, "diversificationLabels", path="itemStruct.diversificationLabels", optional=True)
    diversification_labels = [str(label) for label in labels_raw if label not in (None, "")]
    hashtags = parse_hashtags(item)
    music = parse_music(item)

    return ParsedItem(
        post_id=str(post_id_raw),
        content_type=get_content_type(item),
        description_preview=str(description_preview) if description_preview is not None else None,
        description=None,
        description_length=None,
        description_keywords=None,
        location_created=str(location_created) if location_created is not None else None,
        diversification_labels=diversification_labels,
        metrics=metrics,
        author=author,
        hashtags=hashtags,
        music=music,
    )
