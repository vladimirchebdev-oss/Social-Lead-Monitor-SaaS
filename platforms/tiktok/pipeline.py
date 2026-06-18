"""Parse and persist TikTok scrape results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from platforms.tiktok.fetch import TikTokRawScrape
from platforms.tiktok.parsers.comments import ParsedComment, parse_comments_from_payloads
from platforms.tiktok.parsers.description import apply_customtdk
from platforms.tiktok.parsers.item import ParsedItem, parse_item
from platforms.tiktok.store import save_post


@dataclass(slots=True)
class TikTokParsedScrape:
    item: ParsedItem
    comments: list[ParsedComment]


@dataclass(slots=True)
class CommentStats:
    total: int
    metric: int | None
    author_comments: int
    audience: int


def parse_scrape(scrape: TikTokRawScrape) -> TikTokParsedScrape | None:
    if scrape.item_struct is None:
        return None

    item = parse_item(scrape.item_struct)
    if item is None:
        return None

    if scrape.customtdk_payload:
        apply_customtdk(item, scrape.customtdk_payload)

    comments = parse_comments_from_payloads(scrape.comment_payloads, item.post_id)
    return TikTokParsedScrape(item=item, comments=comments)


def comment_stats(item: ParsedItem, comments: list[ParsedComment]) -> CommentStats:
    author_id = item.author.tiktok_id
    author_comments = sum(1 for c in comments if c.user.uid == author_id)
    return CommentStats(
        total=len(comments),
        metric=item.metrics.comments,
        author_comments=author_comments,
        audience=len(comments) - author_comments,
    )


def save_scrape(url: str, parsed: TikTokParsedScrape) -> None:
    save_post(url, parsed.item, parsed.comments)


def merge_offline_payloads(
    scrape: TikTokRawScrape,
    *,
    comment_json: list[dict[str, Any]] | None = None,
    customtdk_json: dict[str, Any] | None = None,
) -> TikTokRawScrape:
    if comment_json:
        scrape.comment_payloads.extend(comment_json)
    if customtdk_json:
        scrape.customtdk_payload = customtdk_json
    return scrape
