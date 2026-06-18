"""TikTok post URL helpers."""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

TIKTOK_PATH_RE = re.compile(
    r"^/@(?P<username>[^/]+)/(?P<content_type>video|photo)/(?P<post_id>\d+)/?$",
    re.IGNORECASE,
)


def clean_tiktok_url(url: str) -> str:
    """Strip query/fragment and validate TikTok post URL path."""
    parts = urlsplit(url.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError(f"Invalid TikTok URL: {url}")

    clean = urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))
    if not TIKTOK_PATH_RE.match(parts.path):
        raise ValueError(f"Unsupported TikTok URL format: {url}")
    return clean
