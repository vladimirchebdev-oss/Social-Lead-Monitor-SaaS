#!/usr/bin/env python3
"""Fetch a TikTok post and save parsed data to PostgreSQL."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from browser.session import path as session_path
from platforms.tiktok import (
    TikTokRawScrape,
    comment_stats,
    fetch_post,
    merge_offline_payloads,
    normalize_tiktok_url,
    parse_scrape,
    save_scrape,
)
from platforms.tiktok.parsers.extract import extract_item_struct_from_html

DEFAULT_URL = "https://www.tiktok.com/@._049069/video/7632399552070372629"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("fetch_tiktok")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch TikTok post and save to PostgreSQL")
    parser.add_argument("--url", default=DEFAULT_URL, help="TikTok post URL")
    parser.add_argument("--file", type=Path, help="Saved HTML instead of browser")
    parser.add_argument(
        "--comments-json",
        type=Path,
        nargs="*",
        default=[],
        help="Saved comment API JSON files (offline testing)",
    )
    parser.add_argument(
        "--customtdk-json",
        type=Path,
        default=None,
        help="Saved customtdk API JSON (offline testing)",
    )
    parser.add_argument("--headless", action="store_true", help="Headless browser")
    parser.add_argument(
        "--skip-captcha-pause",
        action="store_true",
        help="Ignore captcha overlays (headed only)",
    )
    parser.add_argument(
        "--session",
        type=Path,
        default=None,
        help=f"Session file (default: {session_path()})",
    )
    parser.add_argument(
        "--no-save-session",
        action="store_true",
        help="Do not persist session after fetch",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_url = args.url.strip()

    if args.file:
        try:
            canonical_url = normalize_tiktok_url(input_url)
        except ValueError as exc:
            logger.error("Invalid URL: %s", exc)
            return 1
        logger.info("Loading HTML from file: %s", args.file)
        scrape = TikTokRawScrape(
            url=canonical_url,
            item_struct=extract_item_struct_from_html(args.file.read_text(encoding="utf-8")),
        )
    else:
        logger.info("Fetching post: %s", input_url)
        scrape = fetch_post(
            input_url,
            headless=args.headless,
            skip_captcha_pause=args.skip_captcha_pause,
            session=args.session,
            save_session_flag=not args.no_save_session,
        )
        canonical_url = scrape.url

    comment_json = [
        data
        for path in args.comments_json
        for data in [json.loads(path.read_text(encoding="utf-8"))]
        if isinstance(data, dict)
    ]
    customtdk_json = (
        json.loads(args.customtdk_json.read_text(encoding="utf-8"))
        if args.customtdk_json
        else None
    )
    merge_offline_payloads(
        scrape,
        comment_json=comment_json or None,
        customtdk_json=customtdk_json if isinstance(customtdk_json, dict) else None,
    )

    parsed = parse_scrape(scrape)
    if parsed is None:
        logger.error("itemStruct not found — save cancelled")
        return 1

    save_scrape(canonical_url, parsed)
    stats = comment_stats(parsed.item, parsed.comments)

    logger.info(
        "Saved post_id=%s type=%s views=%s likes=%s hashtags=%s "
        "description=%s keywords=%s comments=%s (metric=%s, author_comments=%s, audience=%s)",
        parsed.item.post_id,
        parsed.item.content_type,
        parsed.item.metrics.views,
        parsed.item.metrics.likes,
        len(parsed.item.hashtags),
        parsed.item.description_length or 0,
        len(parsed.item.description_keywords or []),
        stats.total,
        stats.metric,
        stats.author_comments,
        stats.audience,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
