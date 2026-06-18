"""Playwright fetch in a child process (sync API breaks inside asyncio threads on Windows)."""

from __future__ import annotations


def fetch_video_job(url: str, show_browser: bool) -> dict:
    from platforms.registry import fetch_video
    from web.serialize import fetch_result_dict

    result = fetch_video(url, show_browser=show_browser)
    return fetch_result_dict(result)
