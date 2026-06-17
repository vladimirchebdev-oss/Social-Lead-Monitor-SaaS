"""Extract itemStruct from the first document response."""

from __future__ import annotations

import json
import logging
from typing import Any

from parsers.tiktok.extract_helper import get_block

logger = logging.getLogger(__name__)

REHYDRATION_MARKER = "__UNIVERSAL_DATA_FOR_REHYDRATION__"
REHYDRATION_SELECTOR = 'script[id="__UNIVERSAL_DATA_FOR_REHYDRATION__"]'

# Playwright wait_for_function: true when itemStruct.stats is in the page.
ITEM_STRUCT_READY_JS = """
() => {
    const el = document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");
    if (!el || !el.textContent) return false;
    try {
        const data = JSON.parse(el.textContent);
        const item = data?.__DEFAULT_SCOPE__?.["webapp.video-detail"]?.itemInfo?.itemStruct;
        return Boolean(item && item.stats);
    } catch {
        return false;
    }
}
"""


def extract_item_struct(html: str) -> dict[str, Any] | None:
    """Single entry point for reading TikTok post data from HTML."""
    try:
        marker_index = html.find(REHYDRATION_MARKER)
        if marker_index == -1:
            logger.error("[MISS] __UNIVERSAL_DATA_FOR_REHYDRATION__ — script не найден")
            return None

        json_start = html.find(">", marker_index) + 1
        json_end = html.find("</script>", json_start)
        if json_start <= 0 or json_end == -1:
            logger.error("[MISS] rehydration JSON — не удалось выделить содержимое script")
            return None

        payload = json.loads(html[json_start:json_end])
        scope = get_block(payload, "__DEFAULT_SCOPE__", path="rehydration.__DEFAULT_SCOPE__")
        if scope is None:
            return None

        video_detail = get_block(scope, "webapp.video-detail", path="rehydration.webapp.video-detail")
        if video_detail is None:
            return None

        item_info = get_block(video_detail, "itemInfo", path="itemStruct.itemInfo")
        if item_info is None:
            return None

        item_struct = get_block(item_info, "itemStruct", path="itemStruct")
        return item_struct
    except json.JSONDecodeError as exc:
        logger.error("[MISS] rehydration JSON — ошибка парсинга: %s", exc)
        return None
    except Exception as exc:
        logger.error("[MISS] itemStruct — неожиданная ошибка: %s", exc)
        return None
