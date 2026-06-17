#!/usr/bin/env python3
"""Open TikTok in browser for manual inspection."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Browser, Page, Playwright, sync_playwright

DEFAULT_URL = "https://www.tiktok.com/"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TIKTOK_API_PATTERN = re.compile(r"tiktok|byteoversea|musical\.ly|snssdk", re.I)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Open TikTok in browser and save inspection artifacts."
    )
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--save-artifacts", action="store_true")
    parser.add_argument("--keep-open", action="store_true")
    parser.add_argument("--wait-ms", type=int, default=8000)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    return parser.parse_args()


def slug_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/") or "home"
    return re.sub(r"[^\w\-@.]", "_", path)[:80] or "page"


def session_dir(base: Path, url: str) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    folder = base / f"{ts}_{slug_from_url(url)}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def attach_network_logger(page: Page, log: list[dict[str, Any]]) -> None:
    def on_response(response) -> None:
        url = response.url
        if not TIKTOK_API_PATTERN.search(url):
            return
        entry: dict[str, Any] = {
            "time": datetime.now(timezone.utc).isoformat(),
            "method": response.request.method,
            "url": url,
            "status": response.status,
            "resource_type": response.request.resource_type,
        }
        try:
            if "json" in (response.headers.get("content-type") or "").lower():
                body = response.json()
                if isinstance(body, dict):
                    entry["json_keys"] = list(body.keys())[:30]
                entry["json_preview"] = json.dumps(body, ensure_ascii=False)[:2000]
        except Exception:
            entry["json_preview"] = None
        log.append(entry)

    page.on("response", on_response)


def launch_browser(playwright: Playwright, headless: bool) -> Browser:
    return playwright.chromium.launch(
        headless=headless,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
    )


def create_page(browser: Browser) -> Page:
    context = browser.new_context(
        viewport={"width": 1440, "height": 900},
        locale="en-US",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
    )
    context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
    )
    return context.new_page()


def save_artifacts(
    page: Page,
    folder: Path,
    url: str,
    network_log: list[dict[str, Any]],
) -> None:
    meta = {
        "url": url,
        "final_url": page.url,
        "title": page.title(),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    page.screenshot(path=str(folder / "screenshot.jpg"), full_page=True, type="jpeg")
    (folder / "page.html").write_text(page.content(), encoding="utf-8")
    (folder / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (folder / "network.json").write_text(
        json.dumps(network_log, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nArtifacts saved to: {folder}")
    print("  - screenshot.jpg")
    print("  - page.html")
    print("  - meta.json")
    print(f"  - network.json ({len(network_log)} API responses)")


def print_hints(headless: bool, folder: Path | None) -> None:
    print("\n--- Hints ---")
    print("1. DevTools (F12) -> Elements: DOM and data-e2e attributes.")
    print("2. Network -> Fetch/XHR: JSON with video metadata.")
    if folder:
        print(f"3. Server artifacts: {folder}")
    if headless:
        print("4. For interactive mode use --headed or VNC.")
    print("5. Send me URL, CSS selector, or API endpoint name when ready.\n")


def main() -> int:
    args = parse_args()
    headless = args.headless and not args.headed
    save_flag = args.save_artifacts or headless

    if not args.url.startswith("http"):
        print("Error: --url must start with http(s)://", file=sys.stderr)
        return 1

    folder = session_dir(args.output_dir, args.url) if save_flag else None
    network_log: list[dict[str, Any]] = []

    mode = "headless" if headless else "headed (window)"
    print(f"Opening: {args.url}")
    print(f"Mode: {mode}")

    with sync_playwright() as playwright:
        browser = launch_browser(playwright, headless=headless)
        page = create_page(browser)
        attach_network_logger(page, network_log)
        try:
            page.goto(args.url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(args.wait_ms)
            if save_flag and folder:
                save_artifacts(page, folder, args.url, network_log)
            print_hints(headless, folder)
            if args.keep_open or not headless:
                if headless and not args.keep_open:
                    time.sleep(3)
                else:
                    print("Browser open. Press Enter to close...")
                    try:
                        input()
                    except KeyboardInterrupt:
                        print("\nClosing.")
        finally:
            browser.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())