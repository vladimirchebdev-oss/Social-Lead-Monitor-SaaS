"""Parse TikTok comments from intercepted API payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from platforms.tiktok.parsers.extract_helper import get_block, get_field, to_int


@dataclass(slots=True)
class ParsedCommentUser:
    uid: str
    nickname: str | None
    unique_id: str | None


@dataclass(slots=True)
class ParsedComment:
    comment_id: str
    post_id: str
    text: str | None
    create_time: int | None
    comment_language: str | None
    digg_count: int | None
    is_author_digged: bool
    reply_comment_total: int | None
    is_reply: bool
    parent_comment_id: str | None
    user: ParsedCommentUser


def _parse_comment_user(data: dict[str, Any]) -> ParsedCommentUser | None:
    user = get_block(data, "user", path="comment.user")
    if user is None:
        return None

    uid = get_field(user, "uid", path="comment.user.uid")
    if not uid:
        return None

    nickname = get_field(user, "nickname", path="comment.user.nickname", optional=True)
    unique_id = get_field(user, "unique_id", path="comment.user.unique_id", optional=True)
    if unique_id is None:
        unique_id = get_field(user, "uniqueId", path="comment.user.uniqueId", optional=True)

    return ParsedCommentUser(
        uid=str(uid),
        nickname=str(nickname) if nickname is not None else None,
        unique_id=str(unique_id) if unique_id is not None else None,
    )


def parse_comment(data: dict[str, Any], post_id: str) -> list[ParsedComment]:
    """Parse one comment object and optional inline reply_comment children."""
    cid = get_field(data, "cid", path="comment.cid")
    if not cid:
        return []

    reply_id_raw = data.get("reply_id", "0")
    reply_id = str(reply_id_raw) if reply_id_raw is not None else "0"
    is_reply = reply_id not in ("0", "")

    user = _parse_comment_user(data)
    if user is None:
        return []

    reply_total = None
    if not is_reply:
        reply_total = to_int(data.get("reply_comment_total"))

    comment = ParsedComment(
        comment_id=str(cid),
        post_id=post_id,
        text=get_field(data, "text", path="comment.text", optional=True),
        create_time=to_int(get_field(data, "create_time", path="comment.create_time", optional=True)),
        comment_language=get_field(data, "comment_language", path="comment.comment_language", optional=True),
        digg_count=to_int(get_field(data, "digg_count", path="comment.digg_count", optional=True)),
        is_author_digged=bool(data.get("is_author_digged", False)),
        reply_comment_total=reply_total,
        is_reply=is_reply,
        parent_comment_id=reply_id if is_reply else None,
        user=user,
    )

    results = [comment]

    reply_comments = data.get("reply_comment")
    if isinstance(reply_comments, list):
        for child in reply_comments:
            if isinstance(child, dict):
                results.extend(parse_comment(child, post_id))

    return results


def parse_comments_from_payloads(payloads: list[dict[str, Any]], post_id: str) -> list[ParsedComment]:
    """Flatten all intercepted comment API payloads, dedupe by cid."""
    seen: set[str] = set()
    comments: list[ParsedComment] = []

    for payload in payloads:
        raw_comments = payload.get("comments")
        if not isinstance(raw_comments, list):
            continue
        for entry in raw_comments:
            if not isinstance(entry, dict):
                continue
            for parsed in parse_comment(entry, post_id):
                if parsed.comment_id in seen:
                    continue
                seen.add(parsed.comment_id)
                comments.append(parsed)

    return comments
