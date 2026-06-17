"""Parse TikTok comments."""

from __future__ import annotations

from typing import Any

from parsers.tiktok.types import PostComment


def parse_comment(data: dict[str, Any]) -> PostComment | None:
    """Один комментарий."""
    return None


def parse_comments_response(payload: dict[str, Any]) -> tuple[list[PostComment], dict[str, Any]]:
    """Ответ API со списком комментариев."""
    return [], {}
