"""Signed in-page XHR using a captured TikTok query template."""

from __future__ import annotations

import json
import logging
from typing import Any

from playwright.sync_api import Page

logger = logging.getLogger(__name__)

STRIP_PARAMS = frozenset(
    {"CategoryType", "itemID", "itemId", "pullType", "aweme_id", "X-Bogus", "X-Gnarly", "msToken"}
)

_XHR_JS = """([template, pageUrl, apiPath, params, stripKeys]) => new Promise((resolve, reject) => {
  const p = new URLSearchParams(template);
  p.set("from_page", "video");
  p.set("referer", pageUrl);
  p.set("root_referer", pageUrl);
  for (const k of stripKeys) p.delete(k);
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== "") p.set(k, String(v));
  }
  const xhr = new XMLHttpRequest();
  xhr.open("GET", apiPath + "?" + p.toString());
  xhr.withCredentials = true;
  xhr.onload = () => resolve({ status: xhr.status, body: xhr.responseText });
  xhr.onerror = () => reject("xhr failed");
  xhr.send();
})"""


def signed_get(
    page: Page,
    template: str,
    api_path: str,
    params: dict[str, Any],
    *,
    label: str = "api",
) -> dict[str, Any] | None:
    try:
        raw = page.evaluate(
            _XHR_JS,
            [template, page.url, api_path, params, list(STRIP_PARAMS)],
        )
    except Exception as exc:
        logger.warning("[MISS] %s XHR failed — %s", label, exc)
        return None

    if raw.get("status") != 200:
        logger.warning("[MISS] %s HTTP %s", label, raw.get("status"))
        return None

    try:
        body = json.loads(raw.get("body") or "")
    except json.JSONDecodeError:
        text = (raw.get("body") or "").strip()
        logger.warning("[MISS] %s returned non-JSON (len=%s)", label, len(text))
        return None

    return body if isinstance(body, dict) else None
