"""Parse TikTok hashtags from textExtra."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from platforms.tiktok.parsers.extract_helper import get_field, get_list, to_int


@dataclass(slots=True)
class ParsedHashtag:
    hashtag_id: str
    name: str
    start_pos: int
    end_pos: int


def parse_hashtags(item: dict[str, Any]) -> list[ParsedHashtag]:
    entries = get_list(item, "textExtra", path="itemStruct.textExtra", optional=True)
    hashtags: list[ParsedHashtag] = []

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue

        hashtag_id = get_field(
            entry,
            "hashtagId",
            path=f"itemStruct.textExtra[{index}].hashtagId",
            optional=True,
        )
        hashtag_name = get_field(
            entry,
            "hashtagName",
            path=f"itemStruct.textExtra[{index}].hashtagName",
            optional=True,
        )
        start_pos = to_int(
            get_field(entry, "start", path=f"itemStruct.textExtra[{index}].start", optional=True)
        )
        end_pos = to_int(get_field(entry, "end", path=f"itemStruct.textExtra[{index}].end", optional=True))

        if not hashtag_id or not hashtag_name or start_pos is None or end_pos is None:
            continue

        hashtags.append(
            ParsedHashtag(
                hashtag_id=str(hashtag_id),
                name=str(hashtag_name),
                start_pos=start_pos,
                end_pos=end_pos,
            )
        )

    return hashtags
