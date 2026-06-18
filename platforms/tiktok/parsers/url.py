"""TikTok post URL helpers."""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

TIKTOK_PATH_RE = re.compile(
    r"^/@(?P<username>[^/]+)/(?P<content_type>video|photo)/(?P<post_id>\d+)/?$",
    re.IGNORECASE,
)

# Short links from mobile share (vt/vm/t) expand to /@user/video/... in the browser.
SHORT_TIKTOK_HOSTS = frozenset(
    {
        "vt.tiktok.com",
        "vm.tiktok.com",
        "t.tiktok.com",
    }
)

_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)


def _host(url: str) -> str:
    host = urlsplit(url.strip()).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def is_short_tiktok_url(url: str) -> bool:
    return _host(url) in SHORT_TIKTOK_HOSTS


def is_canonical_tiktok_post_url(url: str) -> bool:
    return bool(TIKTOK_PATH_RE.match(urlsplit(url.strip()).path))


def clean_tiktok_url(url: str) -> str:
    """Strip query/fragment and validate canonical TikTok post URL path."""
    parts = urlsplit(url.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError(f"Invalid TikTok URL: {url}")

    if not TIKTOK_PATH_RE.match(parts.path):
        raise ValueError(f"Unsupported TikTok URL format: {url}")

    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def expand_tiktok_url(url: str) -> str:
    """Follow HTTP redirects for short/mobile TikTok links."""
    request = Request(
        url.strip(),
        headers={"User-Agent": _USER_AGENT, "Accept": "text/html"},
        method="GET",
    )
    with urlopen(request, timeout=20) as response:
        return response.geturl()


def normalize_tiktok_url(url: str) -> str:
    """Resolve short links and return canonical post URL without query."""
    stripped = url.strip()
    if is_canonical_tiktok_post_url(stripped):
        return clean_tiktok_url(stripped)
    return clean_tiktok_url(expand_tiktok_url(stripped))


def resolve_tiktok_url(input_url: str, page_url: str | None = None) -> str:
    """Pick the best canonical URL after optional browser navigation."""
    for candidate in (page_url, input_url):
        if not candidate:
            continue
        try:
            return clean_tiktok_url(candidate)
        except ValueError:
            continue
    return normalize_tiktok_url(input_url)
