"""Safe access to itemStruct blocks with logging."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "")
        if not cleaned:
            return None
        try:
            return int(float(cleaned))
        except ValueError:
            return None
    return None


def get_block(parent: dict[str, Any] | None, key: str, *, path: str) -> dict[str, Any] | None:
    try:
        if not isinstance(parent, dict):
            logger.error("[MISS] %s — родительский блок не dict", path)
            return None
        value = parent.get(key)
        if not isinstance(value, dict):
            logger.error("[MISS] %s — блок не найден", path)
            return None
        logger.info("[OK]   %s — блок получен", path)
        return value
    except Exception as exc:
        logger.error("[MISS] %s — ошибка чтения блока: %s", path, exc)
        return None


def get_field(
    block: dict[str, Any] | None,
    key: str,
    *,
    path: str,
    optional: bool = False,
) -> Any | None:
    try:
        if not isinstance(block, dict):
            level = logger.warning if optional else logger.error
            level("[MISS] %s — блок недоступен", path)
            return None
        if key not in block:
            level = logger.warning if optional else logger.error
            level("[MISS] %s — поле отсутствует", path)
            return None
        value = block.get(key)
        if value is None or value == "":
            level = logger.warning if optional else logger.error
            level("[MISS] %s — поле пустое", path)
            return None
        logger.info("[OK]   %s = %r", path, value)
        return value
    except Exception as exc:
        level = logger.warning if optional else logger.error
        level("[MISS] %s — ошибка чтения поля: %s", path, exc)
        return None


def get_list(
    parent: dict[str, Any] | None,
    key: str,
    *,
    path: str,
    optional: bool = True,
) -> list[Any]:
    try:
        if not isinstance(parent, dict):
            logger.warning("[WARN] %s — родительский блок не dict", path)
            return []
        value = parent.get(key)
        if value is None:
            logger.warning("[WARN] %s — список отсутствует", path)
            return []
        if not isinstance(value, list):
            logger.warning("[WARN] %s — значение не list", path)
            return []
        if not value:
            logger.warning("[WARN] %s — пустой список", path)
            return []
        logger.info("[OK]   %s — %s элемент(ов)", path, len(value))
        return value
    except Exception as exc:
        logger.warning("[WARN] %s — ошибка чтения списка: %s", path, exc)
        return []


def clean_tiktok_url(url: str) -> str:
    if "\\u002F" in url or "\\u002f" in url:
        url = url.encode("utf-8").decode("unicode_escape")
    return url.replace("\\/", "/")
