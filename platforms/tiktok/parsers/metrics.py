"""Parse TikTok engagement metrics."""

from __future__ import annotations

from typing import Any

from platforms.tiktok.parsers.extract_helper import get_block, get_field, to_int
from platforms.tiktok.parsers.types import PostMetrics


def parse_metrics(item: dict[str, Any]) -> PostMetrics | None:
    stats = get_block(item, "stats", path="itemStruct.stats")
    if stats is None:
        return None

    play_count = to_int(get_field(stats, "playCount", path="itemStruct.stats.playCount"))
    digg_count = to_int(get_field(stats, "diggCount", path="itemStruct.stats.diggCount"))
    comment_count = to_int(get_field(stats, "commentCount", path="itemStruct.stats.commentCount"))
    share_count = to_int(get_field(stats, "shareCount", path="itemStruct.stats.shareCount"))
    collect_count = to_int(get_field(stats, "collectCount", path="itemStruct.stats.collectCount"))

    if None in (play_count, digg_count, comment_count, share_count, collect_count):
        return None

    return PostMetrics(
        views=play_count,
        likes=digg_count,
        comments=comment_count,
        shares=share_count,
        saves=collect_count,
    )
