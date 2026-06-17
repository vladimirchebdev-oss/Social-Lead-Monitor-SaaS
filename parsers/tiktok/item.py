"""Unified TikTok video item parser."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from parsers.tiktok.author import ParsedAuthor, parse_author
from parsers.tiktok.extract_helper import get_field, get_list
from parsers.tiktok.hashtags import ParsedHashtag, parse_hashtags
from parsers.tiktok.metrics import parse_metrics
from parsers.tiktok.music import ParsedMusic, parse_music
from parsers.tiktok.types import PostMetrics


@dataclass(slots=True)
class ParsedVideoItem:
    description_preview: str | None
    location_created: str | None
    diversification_labels: list[str]
    metrics: PostMetrics
    author: ParsedAuthor
    hashtags: list[ParsedHashtag]
    music: ParsedMusic | None = None
    description: str | None = None


def parse_video_item(item: dict[str, Any]) -> ParsedVideoItem | None:
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

    return ParsedVideoItem(
        description_preview=str(description_preview) if description_preview is not None else None,
        description=None,
        location_created=str(location_created) if location_created is not None else None,
        diversification_labels=diversification_labels,
        metrics=metrics,
        author=author,
        hashtags=hashtags,
        music=music,
    )
