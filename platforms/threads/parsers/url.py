"""Threads post URL helpers."""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

THREADS_HOSTS = frozenset({"threads.net", "threads.com"})

THREADS_PATH_RE = re.compile(
    r"^/@(?P<username>[^/]+)/post/(?P<post_id>[^/]+)/?$",
    re.IGNORECASE,
)


def _host(url: str) -> str:
    host = urlsplit(url.strip()).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def is_threads_url(url: str) -> bool:
    return _host(url) in THREADS_HOSTS


def is_threads_post_url(url: str) -> bool:
    if not is_threads_url(url):
        return False
    return bool(THREADS_PATH_RE.match(urlsplit(url.strip()).path))


def normalize_threads_url(url: str) -> str:
    raw = url.strip()
    if not raw.startswith("http"):
        raise ValueError("URL должен начинаться с http(s)://")
    if not is_threads_url(raw):
        raise ValueError("Некорректный домен Threads")

    parts = urlsplit(raw)
    path = parts.path.rstrip("/") + "/"
    match = THREADS_PATH_RE.match(path)
    if not match:
        raise ValueError("Ожидается ссылка вида https://www.threads.net/@user/post/ID")

    username = match.group("username")
    post_id = match.group("post_id")
    canonical_path = f"/@{username}/post/{post_id}/"
    return urlunsplit((parts.scheme or "https", parts.netloc, canonical_path, "", ""))
