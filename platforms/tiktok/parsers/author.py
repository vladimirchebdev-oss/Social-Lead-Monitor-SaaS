"""Parse TikTok author data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from platforms.tiktok.parsers.extract_helper import get_block, get_field, to_int, unescape_json_url


@dataclass(slots=True)
class ParsedAuthor:
    tiktok_id: str
    unique_id: str
    nickname: str | None
    avatar_larger: str | None
    create_time: int | None
    verified: bool
    follower_count: int | None
    following_count: int | None
    heart: int | None
    heart_count: int | None
    video_count: int | None
    digg_count: int | None


def parse_author(item: dict[str, Any]) -> ParsedAuthor | None:
    author = get_block(item, "author", path="itemStruct.author")
    author_stats = get_block(item, "authorStats", path="itemStruct.authorStats")
    if author is None or author_stats is None:
        return None

    tiktok_id = get_field(author, "id", path="itemStruct.author.id")
    unique_id = get_field(author, "uniqueId", path="itemStruct.author.uniqueId")
    if not tiktok_id or not unique_id:
        return None

    avatar_raw = get_field(author, "avatarLarger", path="itemStruct.author.avatarLarger", optional=True)
    avatar_larger = unescape_json_url(str(avatar_raw)) if avatar_raw else None

    follower_count = to_int(get_field(author_stats, "followerCount", path="itemStruct.authorStats.followerCount"))
    following_count = to_int(get_field(author_stats, "followingCount", path="itemStruct.authorStats.followingCount"))
    heart = to_int(get_field(author_stats, "heart", path="itemStruct.authorStats.heart"))
    heart_count = to_int(get_field(author_stats, "heartCount", path="itemStruct.authorStats.heartCount"))
    video_count = to_int(get_field(author_stats, "videoCount", path="itemStruct.authorStats.videoCount"))
    digg_count = to_int(get_field(author_stats, "diggCount", path="itemStruct.authorStats.diggCount"))

    if None in (follower_count, following_count, heart, heart_count, video_count, digg_count):
        return None

    verified = bool(author.get("verified", False))
    nickname = get_field(author, "nickname", path="itemStruct.author.nickname", optional=True)
    create_time = to_int(get_field(author, "createTime", path="itemStruct.author.createTime", optional=True))

    return ParsedAuthor(
        tiktok_id=str(tiktok_id),
        unique_id=str(unique_id),
        nickname=str(nickname) if nickname is not None else None,
        avatar_larger=avatar_larger,
        create_time=create_time,
        verified=verified,
        follower_count=follower_count,
        following_count=following_count,
        heart=heart,
        heart_count=heart_count,
        video_count=video_count,
        digg_count=digg_count,
    )
