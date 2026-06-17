"""Parse TikTok music block."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from parsers.tiktok.extract_helper import clean_tiktok_url, get_block, get_field, to_int


@dataclass(slots=True)
class ParsedMusic:
    music_id: str
    title: str
    play_url: str
    cover_large: str
    author_name: str
    original: bool
    duration: int


def parse_music(item: dict[str, Any]) -> ParsedMusic | None:
    music = get_block(item, "music", path="itemStruct.music")
    if music is None:
        return None

    music_id = get_field(music, "id", path="itemStruct.music.id")
    title = get_field(music, "title", path="itemStruct.music.title")
    play_url_raw = get_field(music, "playUrl", path="itemStruct.music.playUrl")
    cover_large_raw = get_field(music, "coverLarge", path="itemStruct.music.coverLarge")
    author_name = get_field(music, "authorName", path="itemStruct.music.authorName")
    duration = to_int(get_field(music, "duration", path="itemStruct.music.duration"))

    if not all([music_id, title, play_url_raw, cover_large_raw, author_name]) or duration is None:
        return None

    original_value = music.get("original")
    if original_value is None:
        return None

    return ParsedMusic(
        music_id=str(music_id),
        title=str(title),
        play_url=clean_tiktok_url(str(play_url_raw)),
        cover_large=clean_tiktok_url(str(cover_large_raw)),
        author_name=str(author_name),
        original=bool(original_value),
        duration=duration,
    )
