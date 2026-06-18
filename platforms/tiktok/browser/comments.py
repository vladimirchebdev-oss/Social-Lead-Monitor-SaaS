"""TikTok comment API: cursor pagination via in-page XHR."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from playwright.sync_api import Page

from platforms.tiktok.browser.xhr import signed_get
from platforms.tiktok.parsers.comments import parse_comments_from_payloads

logger = logging.getLogger(__name__)

PAGE_COUNT = 50
_LIST_PATH = "/api/comment/list/"
_REPLY_PATH = "/api/comment/list/reply/"


def _has_more(data: dict[str, Any]) -> bool:
    return int(data.get("has_more") or 0) != 0


def _parse_list_body(body: dict[str, Any]) -> dict[str, Any] | None:
    if body.get("status_code", 0) != 0:
        logger.warning(
            "Comment API status_code=%s: %s",
            body.get("status_code"),
            body.get("status_msg"),
        )
        return None
    if isinstance(body.get("comments"), list):
        return body
    return None


def _request_page(
    page: Page,
    template: str,
    page_url: str,
    aweme_id: str,
    cursor: int = 0,
    *,
    reply_id: str | None = None,
) -> dict[str, Any] | None:
    params = {"aweme_id": aweme_id, "count": PAGE_COUNT, "cursor": cursor}
    if reply_id:
        params["comment_id"] = reply_id
    body = signed_get(
        page,
        template,
        _REPLY_PATH if reply_id else _LIST_PATH,
        params,
        label="comment",
    )
    return body


def _paginate_list(
    page: Page,
    template: str,
    page_url: str,
    aweme_id: str,
    *,
    first_page: dict[str, Any] | None = None,
    on_pause: Callable[[], None] | None = None,
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    cursor = 0

    if first_page is not None:
        page_data = _parse_list_body(first_page)
        if page_data is None:
            return payloads
        payloads.append(page_data)
        logger.info(
            "browser page: %s top-level (has_more=%s)",
            len(page_data["comments"]),
            page_data.get("has_more"),
        )
        if not _has_more(page_data):
            return payloads
        cursor = int(page_data.get("cursor") or 0)

    while True:
        if on_pause:
            on_pause()
        body = _request_page(page, template, page_url, aweme_id, cursor)
        if body is None:
            break
        page_data = _parse_list_body(body)
        if page_data is None:
            break
        payloads.append(page_data)
        logger.info(
            "cursor=%s: %s top-level (has_more=%s)",
            cursor,
            len(page_data["comments"]),
            page_data.get("has_more"),
        )
        if not _has_more(page_data):
            break
        cursor = int(page_data.get("cursor") or 0)

    return payloads


def _fetch_reply_threads(
    page: Page,
    template: str,
    page_url: str,
    aweme_id: str,
    payloads: list[dict[str, Any]],
    *,
    on_pause: Callable[[], None] | None = None,
) -> None:
    existing = parse_comments_from_payloads(payloads, aweme_id)
    for comment in existing:
        if on_pause:
            on_pause()
        if comment.is_reply or not comment.reply_comment_total:
            continue
        have = sum(
            1 for c in existing
            if c.is_reply and c.parent_comment_id == comment.comment_id
        )
        if have >= comment.reply_comment_total:
            continue
        body = _request_page(
            page, template, page_url, aweme_id, reply_id=comment.comment_id
        )
        parsed = _parse_list_body(body) if body else None
        if parsed and parsed["comments"]:
            payloads.append(parsed)
            existing = parse_comments_from_payloads(payloads, aweme_id)
            logger.info(
                "Reply thread %s: %s comments",
                comment.comment_id,
                len(parsed["comments"]),
            )


def fetch_comments(
    page: Page,
    template: str,
    aweme_id: str,
    *,
    first_page: dict[str, Any] | None = None,
    on_pause: Callable[[], None] | None = None,
) -> list[dict[str, Any]]:
    """Top-level list + reply threads via signed in-page XHR."""
    payloads = _paginate_list(
        page, template, page.url, aweme_id, first_page=first_page, on_pause=on_pause
    )
    _fetch_reply_threads(
        page, template, page.url, aweme_id, payloads, on_pause=on_pause
    )
    total = sum(len(p.get("comments") or []) for p in payloads)
    logger.info("Collected %s comment payload(s), %s raw items", len(payloads), total)
    return payloads
