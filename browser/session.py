"""Persist Playwright storage state (cookies, localStorage) for TikTok."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserContext

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SESSION = ROOT / "session.json"

VIEWPORT = {"width": 1280, "height": 720}
LOCALE = "en-US"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

_STEALTH_JS = (
    "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
)

CHROMIUM_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
]

_SAMESITE_MAP = {
    "no_restriction": "None",
    "none": "None",
    "lax": "Lax",
    "strict": "Strict",
}


def path() -> Path:
    """Default session file path."""
    return DEFAULT_SESSION


def _normalize_samesite(value: Any) -> str:
    if value is None:
        return "Lax"
    key = str(value).lower()
    return _SAMESITE_MAP.get(key, "Lax")


def _extension_cookie(raw: dict[str, Any]) -> dict[str, Any]:
    cookie: dict[str, Any] = {
        "name": raw["name"],
        "value": raw["value"],
        "domain": raw["domain"],
        "path": raw.get("path") or "/",
        "httpOnly": bool(raw.get("httpOnly")),
        "secure": bool(raw.get("secure")),
        "sameSite": _normalize_samesite(raw.get("sameSite")),
    }
    if raw.get("session"):
        cookie["expires"] = -1
    elif "expirationDate" in raw:
        cookie["expires"] = raw["expirationDate"]
    return cookie


def load(session_path: Path | None = None) -> dict[str, Any] | None:
    """Load storage_state dict from file. Supports Playwright and browser cookie export."""
    p = session_path or path()
    if not p.is_file():
        return None

    data = json.loads(p.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {"cookies": [_extension_cookie(c) for c in data], "origins": []}
    if isinstance(data, dict) and isinstance(data.get("cookies"), list):
        # Cookies only — fresh msToken/localStorage from the live page each run.
        return {"cookies": data["cookies"], "origins": []}

    logger.warning("Unknown session format: %s", p)
    return None


def new_context(
    browser: Browser,
    *,
    session_path: Path | None = None,
    **overrides: object,
) -> BrowserContext:
    """Browser context with default TikTok profile; loads session if file exists."""
    opts: dict = {
        "viewport": VIEWPORT,
        "locale": LOCALE,
        "user_agent": USER_AGENT,
    }
    state = load(session_path)
    if state is not None:
        opts["storage_state"] = state
        logger.info("Session loaded: %s", session_path or path())
    opts.update(overrides)
    context = browser.new_context(**opts)
    context.add_init_script(_STEALTH_JS)
    return context


def save(context: BrowserContext, session_path: Path | None = None) -> Path:
    """Persist cookies and localStorage to disk (Playwright format)."""
    p = session_path or path()
    p.parent.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(p))
    logger.info("Session saved: %s", p)
    return p
