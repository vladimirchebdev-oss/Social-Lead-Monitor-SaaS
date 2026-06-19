"""Platform detection and fetch routing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

from platforms.tiktok import fetch_post as fetch_tiktok_post
from platforms.tiktok.parsers.url import normalize_tiktok_url
from platforms.tiktok.pipeline import CommentStats, TikTokParsedScrape, comment_stats, parse_scrape
from platforms.threads.parsers.url import normalize_threads_url


class PlatformId(str, Enum):
    TIKTOK = "tiktok"
    THREADS = "threads"


@dataclass(slots=True, frozen=True)
class PlatformInfo:
    id: PlatformId
    name: str
    available: bool
    host_patterns: tuple[str, ...]


PLATFORMS: tuple[PlatformInfo, ...] = (
    PlatformInfo(PlatformId.TIKTOK, "TikTok", True, ("tiktok.com", "vt.tiktok.com", "vm.tiktok.com")),
    PlatformInfo(PlatformId.THREADS, "Threads", False, ("threads.net", "threads.com")),
)


@dataclass(slots=True)
class FetchResult:
    platform: PlatformId
    url: str
    parsed: TikTokParsedScrape
    stats: CommentStats


def _normalize_host(url: str) -> str:
    host = urlparse(url.strip()).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def detect_platform(url: str) -> PlatformInfo | None:
    host = _normalize_host(url)
    if not host:
        return None
    for platform in PLATFORMS:
        if any(host == pattern or host.endswith(f".{pattern}") for pattern in platform.host_patterns):
            return platform
    return None


def fetch_video(url: str, *, show_browser: bool) -> FetchResult:
    platform = detect_platform(url)
    if platform is None:
        raise ValueError("Неподдерживаемая платформа или некорректный URL")
    if not platform.available:
        raise ValueError(f"{platform.name} пока недоступен")

    if platform.id == PlatformId.TIKTOK:
        fetch_url = normalize_tiktok_url(url)
        scrape = fetch_tiktok_post(fetch_url, headless=not show_browser)
        parsed = parse_scrape(scrape)
        if parsed is None:
            raise ValueError("Не удалось получить данные видео")
        return FetchResult(
            platform=platform.id,
            url=scrape.url or fetch_url,
            parsed=parsed,
            stats=comment_stats(parsed.item, parsed.comments),
        )

    if platform.id == PlatformId.THREADS:
        fetch_url = normalize_threads_url(url)
        from platforms.threads import fetch_post as fetch_threads_post
        from platforms.threads.pipeline import parse_scrape as parse_threads_scrape

        scrape = fetch_threads_post(fetch_url, headless=not show_browser)
        parsed = parse_threads_scrape(scrape)
        if parsed is None:
            raise ValueError("Не удалось получить данные поста Threads")
        return FetchResult(
            platform=platform.id,
            url=scrape.url or fetch_url,
            parsed=parsed,
            stats=comment_stats(parsed.item, parsed.comments),
        )

    raise ValueError(f"Платформа {platform.name} не реализована")
