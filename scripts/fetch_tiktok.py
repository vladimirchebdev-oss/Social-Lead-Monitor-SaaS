#!/usr/bin/env python3
"""Fetch a TikTok post and save parsed data to PostgreSQL."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db.repository import save_video_post
from parsers.tiktok.extract import (
    ITEM_STRUCT_READY_JS,
    REHYDRATION_SELECTOR,
    extract_item_struct,
)
from parsers.tiktok.item import parse_video_item
from parsers.tiktok.url import parse_tiktok_url
from playwright.sync_api import sync_playwright

TIKTOK_URL = (
    "https://www.tiktok.com/@reyzirserials24/video/7630355210468232468?is_from_webapp=1&sender_device=pc"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("fetch_tiktok")


def fetch_page_html(url: str, *, headless: bool = False) -> str:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_selector(REHYDRATION_SELECTOR, state="attached", timeout=60_000)
            page.wait_for_function(ITEM_STRUCT_READY_JS, timeout=60_000)
            logger.info("itemStruct loaded in page")
            return page.content()
        finally:
            browser.close()


def load_html_from_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch TikTok video and save to PostgreSQL")
    parser.add_argument(
        "--file",
        type=Path,
        help="Read saved HTML response instead of opening the browser",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser without window (for server)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        parsed_url = parse_tiktok_url(TIKTOK_URL)
    except ValueError as exc:
        logger.error("Invalid URL: %s", exc)
        return 1

    if parsed_url.content_type == "photo":
        logger.warning("Photo parsing is not implemented yet")
        return 0

    if args.file:
        logger.info("Loading HTML from file: %s", args.file)
        html = load_html_from_file(args.file)
    else:
        logger.info("Fetching HTML: %s", parsed_url.clean_url)
        html = fetch_page_html(parsed_url.clean_url, headless=args.headless)

    item = extract_item_struct(html)
    if item is None:
        logger.error("itemStruct not found — save cancelled")
        return 1

    data = parse_video_item(item)
    if data is None:
        logger.error("Required itemStruct blocks missing — save cancelled")
        return 1

    save_video_post(parsed_url, data)
    logger.info(
        "Saved post_id=%s views=%s likes=%s hashtags=%s",
        parsed_url.post_id,
        data.metrics.views,
        data.metrics.likes,
        len(data.hashtags),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
