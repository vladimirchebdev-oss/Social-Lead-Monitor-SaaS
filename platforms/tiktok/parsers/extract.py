"""Extract itemStruct from HTML rehydration or API JSON."""

from __future__ import annotations

import json
import logging
from typing import Any

from platforms.tiktok.parsers.extract_helper import get_block

logger = logging.getLogger(__name__)

REHYDRATION_MARKER = "__UNIVERSAL_DATA_FOR_REHYDRATION__"
REHYDRATION_SELECTOR = 'script[id="__UNIVERSAL_DATA_FOR_REHYDRATION__"]'

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


def _unwrap_item_struct(data: dict[str, Any]) -> dict[str, Any] | None:
    item_info = data.get("itemInfo")
    if isinstance(item_info, dict):
        item_struct = item_info.get("itemStruct")
        if isinstance(item_struct, dict):
            return item_struct

    scope = data.get("__DEFAULT_SCOPE__")
    if isinstance(scope, dict):
        video_detail = scope.get("webapp.video-detail")
        if isinstance(video_detail, dict):
            item_info = video_detail.get("itemInfo")
            if isinstance(item_info, dict):
                item_struct = item_info.get("itemStruct")
                if isinstance(item_struct, dict):
                    return item_struct

    item_struct = data.get("itemStruct")
    if isinstance(item_struct, dict):
        return item_struct

    return None


def extract_item_struct_from_html(html: str) -> dict[str, Any] | None:
    """Read itemStruct from the first document HTML response."""
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
        item_struct = _unwrap_item_struct(payload)
        if item_struct is None:
            logger.error("[MISS] itemStruct — не найден в rehydration JSON")
        return item_struct
    except json.JSONDecodeError as exc:
        logger.error("[MISS] rehydration JSON — ошибка парсинга: %s", exc)
        return None
    except Exception as exc:
        logger.error("[MISS] itemStruct — неожиданная ошибка: %s", exc)
        return None


def extract_item_struct_from_json(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Read itemStruct from intercepted /api/item/detail/ JSON."""
    item_struct = _unwrap_item_struct(payload)
    if item_struct is None:
        logger.error("[MISS] itemStruct — не найден в API JSON")
    return item_struct


# Backward-compatible alias
extract_item_struct = extract_item_struct_from_html
