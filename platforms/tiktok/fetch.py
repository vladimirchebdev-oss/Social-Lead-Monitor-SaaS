"""TikTok post fetcher: browser session + API capture."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from browser.session import CHROMIUM_ARGS, new_context, save as save_session
from platforms.tiktok.browser import fetch_comments, fetch_customtdk, solve_if_visible
from platforms.tiktok.parsers.description import parse_customtdk
from platforms.tiktok.parsers.extract import (
    ITEM_STRUCT_READY_JS,
    REHYDRATION_SELECTOR,
    extract_item_struct_from_html,
    extract_item_struct_from_json,
)
from playwright.sync_api import Page, Response, sync_playwright

logger = logging.getLogger(__name__)

_POLL_MS = 500
_ITEM_WAIT_S = 45
_TEMPLATE_WAIT_S = 30


@dataclass(slots=True)
class TikTokRawScrape:
    item_struct: dict[str, Any] | None = None
    comment_payloads: list[dict[str, Any]] = field(default_factory=list)
    customtdk_payload: dict[str, Any] | None = None


def _is_signed_api(url: str) -> bool:
    return "tiktok.com/api/" in url and "X-Bogus" in url


def _is_template_api(url: str) -> bool:
    return _is_signed_api(url) and "/api/comment/list/" not in url


def _is_comment_list(url: str) -> bool:
    return "/api/comment/list/" in url and "/reply" not in url and _is_signed_api(url)


def _is_customtdk(url: str) -> bool:
    return "/api/customtdk/item" in url


def _try_item_struct(page: Page) -> tuple[dict[str, Any] | None, str]:
    if page.locator(REHYDRATION_SELECTOR).count() == 0:
        return None, page.content()
    try:
        page.wait_for_function(ITEM_STRUCT_READY_JS, timeout=2_000)
    except Exception:
        return None, page.content()
    html = page.content()
    return extract_item_struct_from_html(html), html


def _has_description(payload: dict[str, Any] | None) -> bool:
    parsed = parse_customtdk(payload) if payload else None
    return parsed is not None and parsed.description is not None


def fetch_post(
    url: str,
    *,
    headless: bool = False,
    skip_captcha_pause: bool = False,
    session: Path | None = None,
    save_session_flag: bool = True,
) -> TikTokRawScrape:
    scrape = TikTokRawScrape()
    detail_json: dict[str, Any] | None = None
    api_template: str | None = None
    template_path: str | None = None
    first_comment_page: dict[str, Any] | None = None
    skip_captcha = headless or skip_captcha_pause

    def reset_capture() -> None:
        nonlocal api_template, template_path, first_comment_page
        api_template = None
        template_path = None
        first_comment_page = None
        scrape.customtdk_payload = None

    def tick_captcha() -> bool:
        if solve_if_visible(page, skip=skip_captcha):
            reset_capture()
            return True
        return False

    def on_response(response: Response) -> None:
        nonlocal detail_json, api_template, template_path, first_comment_page
        response_url = response.url
        if _is_template_api(response_url):
            api_template = urlparse(response.request.url).query
            template_path = urlparse(response.request.url).path
        if first_comment_page is None and _is_comment_list(response_url):
            try:
                body = response.json()
                if isinstance(body, dict) and isinstance(body.get("comments"), list):
                    first_comment_page = body
            except Exception:
                pass
        if scrape.customtdk_payload is None and _is_customtdk(response_url):
            try:
                body = response.json()
                if isinstance(body, dict) and isinstance(body.get("itemCustomTDK"), dict):
                    scrape.customtdk_payload = body
            except Exception:
                pass
        if "/api/item/detail" in response_url and detail_json is None:
            try:
                body = response.json()
                if isinstance(body, dict):
                    detail_json = body
            except Exception:
                pass

    logger.info("Launching Chromium (%s)...", "headless" if headless else "headed")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless, args=CHROMIUM_ARGS)
        context = new_context(browser, session_path=session)
        page = context.new_page()
        page.on("response", on_response)

        logger.info("Opening page...")
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        tick_captcha()

        html: str | None = None
        deadline = time.monotonic() + _ITEM_WAIT_S
        while scrape.item_struct is None and time.monotonic() < deadline:
            tick_captcha()
            try:
                page.wait_for_selector(REHYDRATION_SELECTOR, state="attached", timeout=2_000)
                scrape.item_struct, html = _try_item_struct(page)
            except Exception as exc:
                logger.info("itemStruct not ready (%s)", exc.__class__.__name__)
                html = page.content()
            if scrape.item_struct is None:
                page.wait_for_timeout(_POLL_MS)

        if scrape.item_struct is None:
            deadline = time.monotonic() + _TEMPLATE_WAIT_S
            while detail_json is None and time.monotonic() < deadline:
                tick_captcha()
                page.wait_for_timeout(_POLL_MS)
            if html:
                scrape.item_struct = extract_item_struct_from_html(html)
            if scrape.item_struct is None and detail_json is not None:
                scrape.item_struct = extract_item_struct_from_json(detail_json)

        if scrape.item_struct is not None:
            post_id = str(scrape.item_struct.get("id", ""))
            if post_id:

                def wait_template(timeout_s: float = _TEMPLATE_WAIT_S) -> None:
                    deadline = time.monotonic() + timeout_s
                    while api_template is None and time.monotonic() < deadline:
                        tick_captcha()
                        page.wait_for_timeout(_POLL_MS)

                wait_template()
                tick_captcha()
                if api_template is None:
                    logger.error("Signed API template not captured")
                else:
                    logger.info("API template from %s", template_path)
                    if not _has_description(scrape.customtdk_payload):
                        logger.info("Requesting full description...")
                        fetched = fetch_customtdk(page, api_template, post_id)
                        if fetched:
                            scrape.customtdk_payload = fetched
                    else:
                        logger.info("Full description from intercepted customtdk")
                    logger.info("Requesting comments...")
                    scrape.comment_payloads = fetch_comments(
                        page,
                        api_template,
                        post_id,
                        first_page=first_comment_page,
                        on_pause=tick_captcha,
                    )
                    if not scrape.comment_payloads:
                        logger.info("No comments collected")
                        tick_captcha()
                        wait_template()
                        if api_template:
                            logger.info("Retrying comments...")
                            scrape.comment_payloads = fetch_comments(
                                page,
                                api_template,
                                post_id,
                                first_page=first_comment_page,
                                on_pause=tick_captcha,
                            )

        if save_session_flag:
            save_session(context, session_path=session)
        browser.close()

    return scrape
