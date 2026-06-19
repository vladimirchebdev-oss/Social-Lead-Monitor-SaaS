"""Threads post fetch (not implemented yet)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ThreadsRawScrape:
    url: str
    post_id: str | None = None
    item_struct: dict[str, Any] | None = None
    comment_payloads: list[dict[str, Any]] = field(default_factory=list)


def fetch_post(url: str, *, headless: bool = True) -> ThreadsRawScrape:
    """Fetch a Threads post. Parser implementation pending."""
    raise NotImplementedError("Анализ Threads пока в разработке")
