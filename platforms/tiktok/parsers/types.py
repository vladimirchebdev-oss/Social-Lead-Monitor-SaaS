"""Shared TikTok parser types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PostMetrics:
    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None
    saves: int | None = None
