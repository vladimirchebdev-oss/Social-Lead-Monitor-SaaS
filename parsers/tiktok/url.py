"""Parse TikTok post URLs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

TIKTOK_PATH_RE = re.compile(
    r"^/@(?P<username>[^/]+)/(?P<content_type>video|photo)/(?P<post_id>\d+)/?$",
    re.IGNORECASE,
)


@dataclass(slots=True)
class ParsedUrl:
    username: str
    content_type: str
    post_id: str
    clean_url: str


def parse_tiktok_url(url: str) -> ParsedUrl:
    parts = urlsplit(url.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError(f"Invalid TikTok URL: {url}")

    clean_url = urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))
    match = TIKTOK_PATH_RE.match(parts.path)
    if not match:
        raise ValueError(f"Unsupported TikTok URL format: {url}")

    username = f"@{match.group('username')}"
    content_type = match.group("content_type").lower()
    post_id = match.group("post_id")
    return ParsedUrl(
        username=username,
        content_type=content_type,
        post_id=post_id,
        clean_url=clean_url,
    )
