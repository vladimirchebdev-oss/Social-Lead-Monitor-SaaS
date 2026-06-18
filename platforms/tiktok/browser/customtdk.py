"""TikTok customtdk API: full post description via in-page XHR."""

from __future__ import annotations

import logging
from typing import Any

from playwright.sync_api import Page

from platforms.tiktok.browser.xhr import signed_get

logger = logging.getLogger(__name__)

_PATH = "/api/customtdk/item/"


def fetch_customtdk(page: Page, template: str, item_id: str) -> dict[str, Any] | None:
    """Fetch itemCustomTDK payload for a post."""
    body = signed_get(page, template, _PATH, {"itemId": item_id}, label="customtdk")
    if body is None:
        return None

    if int(body.get("status_code") or body.get("statusCode") or 0) != 0:
        logger.warning(
            "customtdk status_code=%s: %s",
            body.get("status_code") or body.get("statusCode"),
            body.get("status_msg"),
        )
        return None

    return body
