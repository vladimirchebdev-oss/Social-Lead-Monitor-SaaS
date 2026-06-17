"""Shared TikTok parser types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ContentType(str, Enum):
    VIDEO = "video"
    PHOTO = "photo"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class PostMetrics:
    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None
    saves: int | None = None


@dataclass(slots=True)
class MediaItem:
    content_type: ContentType = ContentType.UNKNOWN
    post_id: str | None = None
    description: str | None = None
    video_url: str | None = None
    photo_urls: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PostComment:
    comment_id: str | None = None
    text: str | None = None
    author_username: str | None = None
    replies: list[PostComment] = field(default_factory=list)
