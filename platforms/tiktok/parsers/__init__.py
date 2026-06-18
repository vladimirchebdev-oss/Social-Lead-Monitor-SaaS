"""TikTok JSON parsers."""

from platforms.tiktok.parsers.author import ParsedAuthor, parse_author
from platforms.tiktok.parsers.comments import (
    ParsedComment,
    ParsedCommentUser,
    parse_comment,
    parse_comments_from_payloads,
)
from platforms.tiktok.parsers.description import ParsedCustomTdk, apply_customtdk, parse_customtdk
from platforms.tiktok.parsers.extract import (
    extract_item_struct_from_html,
    extract_item_struct_from_json,
)
from platforms.tiktok.parsers.hashtags import ParsedHashtag, parse_hashtags
from platforms.tiktok.parsers.item import ParsedItem, parse_item
from platforms.tiktok.parsers.metrics import parse_metrics
from platforms.tiktok.parsers.music import ParsedMusic, parse_music
from platforms.tiktok.parsers.types import PostMetrics
from platforms.tiktok.parsers.url import clean_tiktok_url

__all__ = [
    "ParsedAuthor",
    "ParsedComment",
    "ParsedCommentUser",
    "ParsedCustomTdk",
    "ParsedHashtag",
    "ParsedItem",
    "ParsedMusic",
    "PostMetrics",
    "apply_customtdk",
    "clean_tiktok_url",
    "extract_item_struct_from_html",
    "extract_item_struct_from_json",
    "parse_author",
    "parse_comment",
    "parse_comments_from_payloads",
    "parse_customtdk",
    "parse_hashtags",
    "parse_item",
    "parse_metrics",
    "parse_music",
]
