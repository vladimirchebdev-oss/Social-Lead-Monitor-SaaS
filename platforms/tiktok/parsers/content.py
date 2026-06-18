"""Detect TikTok post content type from itemStruct."""

from __future__ import annotations

from typing import Any


def get_content_type(item: dict[str, Any]) -> str:
    """Return ``video`` or ``photo`` based on itemStruct fields."""
    image_post = item.get("imagePost")
    if isinstance(image_post, dict) and image_post:
        return "photo"
    return "video"
