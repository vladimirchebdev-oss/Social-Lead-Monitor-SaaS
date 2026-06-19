"""Parse and persist Threads scrape results (stub)."""

from __future__ import annotations

from platforms.threads.fetch import ThreadsRawScrape
from platforms.tiktok.pipeline import TikTokParsedScrape


def parse_scrape(scrape: ThreadsRawScrape) -> TikTokParsedScrape | None:
    raise NotImplementedError("Парсер Threads пока в разработке")
