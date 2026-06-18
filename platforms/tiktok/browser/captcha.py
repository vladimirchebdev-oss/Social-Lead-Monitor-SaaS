"""Detect TikTok captcha overlay and wait for manual solve (headed)."""

from __future__ import annotations

import logging
import time

from playwright.sync_api import Page

logger = logging.getLogger(__name__)

_CAPTCHA_SELECTORS = (
    'iframe[src*="captcha"]',
    'iframe[src*="verify"]',
    'iframe[src*="turing"]',
    '[id*="captcha"]',
    '[id*="verify"]',
    '[class*="captcha"]',
    '[class*="Captcha"]',
    '[class*="verify"]',
    '[class*="secsdk"]',
    '[class*="Turing"]',
)

_VISIBLE_MS = 300
_POLL_MS = 500
_GONE_TIMEOUT_S = 120


def is_visible(page: Page) -> bool:
    for selector in _CAPTCHA_SELECTORS:
        try:
            if page.locator(selector).first.is_visible(timeout=_VISIBLE_MS):
                return True
        except Exception:
            continue
    return False


def solve_if_visible(page: Page, *, skip: bool = False) -> bool:
    """If captcha is on screen, block until user solves it."""
    if skip or not is_visible(page):
        return False
    return _wait_until_solved(page)


def _wait_until_solved(page: Page) -> bool:
    logger.info("Captcha detected")
    print("\n>>> Капча на странице. Пройдите её, затем нажмите Enter <<<\n", flush=True)
    input()

    gone_deadline = time.monotonic() + _GONE_TIMEOUT_S
    while is_visible(page) and time.monotonic() < gone_deadline:
        page.wait_for_timeout(_POLL_MS)

    if is_visible(page):
        logger.warning("Captcha still visible after Enter")
    else:
        logger.info("Captcha cleared")
    return True
