"""Load normalized post data for API responses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from db.connection import get_connection

SUMMARY_COLUMNS = """
    p.post_id,
    'tiktok' AS platform,
    p.url,
    a.nickname,
    a.unique_id,
    a.avatar_larger,
    p.description_preview,
    p.play_count,
    p.digg_count,
    p.comment_count,
    p.share_count,
    p.scraped_at
"""


@dataclass(slots=True)
class PostSummary:
    post_id: str
    platform: str
    post_url: str
    author_name: str | None
    author_username: str | None
    author_avatar_url: str | None
    description_preview: str | None
    views: int | None
    likes: int | None
    comments_count: int | None
    shares_count: int | None
    scraped_at: datetime
    saved_at: datetime | None = None
    is_saved: bool = False


def post_summary_from_row(row: tuple[Any, ...], *, is_saved: bool, saved_at: datetime | None) -> PostSummary:
    return PostSummary(
        post_id=row[0],
        platform=row[1],
        post_url=row[2],
        author_name=row[3],
        author_username=row[4],
        author_avatar_url=row[5],
        description_preview=row[6],
        views=row[7],
        likes=row[8],
        comments_count=row[9],
        shares_count=row[10],
        scraped_at=row[11],
        saved_at=saved_at,
        is_saved=is_saved,
    )


def post_exists(post_id: str) -> bool:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM posts WHERE post_id = %s", (post_id,))
        return cur.fetchone() is not None


def load_inspect_payload(post_id: str, platform: str = "tiktok") -> dict[str, Any] | None:
    """Rebuild fetch_result_dict shape from posts/comments/hashtags tables."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                p.post_id, p.content_type, p.url, p.description, p.description_preview,
                p.description_length, p.description_keywords, p.location_created,
                p.diversification_labels, p.cover_url, p.photo_urls,
                p.play_count, p.digg_count, p.comment_count, p.share_count, p.collect_count,
                a.tiktok_id, a.unique_id, a.nickname, a.avatar_larger, a.create_time, a.verified,
                a.follower_count, a.following_count, a.heart, a.heart_count, a.video_count, a.digg_count,
                m.music_id, m.title, m.play_url, m.cover_large, m.author_name, m.original, m.duration
            FROM posts p
            JOIN authors a ON a.tiktok_id = p.author_id
            LEFT JOIN music m ON m.music_id = p.music_id
            WHERE p.post_id = %s
            """,
            (post_id,),
        )
        row = cur.fetchone()
        if not row:
            return None

        cur.execute(
            """
            SELECT h.hashtag_id, h.name, ph.start_pos, ph.end_pos
            FROM post_hashtags ph
            JOIN hashtags h ON h.hashtag_id = ph.hashtag_id
            WHERE ph.post_id = %s
            ORDER BY ph.start_pos
            """,
            (post_id,),
        )
        hashtag_rows = cur.fetchall()

        cur.execute(
            """
            SELECT
                c.comment_id, c.post_id, c.text, c.create_time, c.comment_language,
                c.digg_count, c.is_author_digged, c.reply_comment_total,
                c.is_reply, c.parent_comment_id,
                a.tiktok_id, a.nickname, a.unique_id
            FROM comments c
            JOIN authors a ON a.tiktok_id = c.author_id
            WHERE c.post_id = %s
            ORDER BY c.create_time NULLS LAST, c.comment_id
            """,
            (post_id,),
        )
        comment_rows = cur.fetchall()

    cover_url = row[9]
    photo_urls = list(row[10]) if row[10] else None
    media: dict[str, Any] | None = None
    if cover_url or photo_urls:
        media = {"video_cover": cover_url, "photo_urls": photo_urls}

    item: dict[str, Any] = {
        "post_id": row[0],
        "content_type": row[1],
        "description": row[3],
        "description_preview": row[4],
        "description_length": row[5],
        "description_keywords": list(row[6]) if row[6] else None,
        "location_created": row[7],
        "diversification_labels": list(row[8]) if row[8] else [],
        "metrics": {
            "views": row[11],
            "likes": row[12],
            "comments": row[13],
            "shares": row[14],
            "saves": row[15],
        },
        "author": {
            "tiktok_id": row[16],
            "unique_id": row[17],
            "nickname": row[18],
            "avatar_larger": row[19],
            "create_time": row[20],
            "verified": row[21],
            "follower_count": row[22],
            "following_count": row[23],
            "heart": row[24],
            "heart_count": row[25],
            "video_count": row[26],
            "digg_count": row[27],
        },
        "hashtags": [
            {"hashtag_id": h[0], "name": h[1], "start_pos": h[2], "end_pos": h[3]}
            for h in hashtag_rows
        ],
        "music": None,
        "media": media,
    }

    if row[28]:
        item["music"] = {
            "music_id": row[28],
            "title": row[29],
            "play_url": row[30],
            "cover_large": row[31],
            "author_name": row[32],
            "original": row[33],
            "duration": row[34],
        }

    comments: list[dict[str, Any]] = []
    author_id = row[16]
    for c in comment_rows:
        comments.append(
            {
                "comment_id": c[0],
                "post_id": c[1],
                "text": c[2],
                "create_time": c[3],
                "comment_language": c[4],
                "digg_count": c[5],
                "is_author_digged": c[6],
                "reply_comment_total": c[7],
                "is_reply": c[8],
                "parent_comment_id": c[9],
                "user": {"uid": c[10], "nickname": c[11], "unique_id": c[12]},
            }
        )

    author_comments = sum(1 for c in comments if c["user"]["uid"] == author_id)
    return {
        "platform": platform,
        "url": row[2],
        "item": item,
        "comments": comments,
        "comment_stats": {
            "total": len(comments),
            "metric": row[13],
            "author_comments": author_comments,
            "audience": len(comments) - author_comments,
        },
    }


def get_post_summary(post_id: str, *, is_saved: bool = False, saved_at: datetime | None = None) -> PostSummary | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {SUMMARY_COLUMNS}
            FROM posts p
            JOIN authors a ON a.tiktok_id = p.author_id
            WHERE p.post_id = %s
            """,
            (post_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return post_summary_from_row(row, is_saved=is_saved, saved_at=saved_at)


def user_has_saved_post(user_id: UUID, post_id: str) -> bool:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT %s = ANY(saved_post_ids) FROM users WHERE id = %s",
            (post_id, user_id),
        )
        row = cur.fetchone()
        return bool(row and row[0])


def user_can_view_post(user_id: UUID, post_id: str) -> bool:
    if user_has_saved_post(user_id, post_id):
        return True
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM users WHERE id = %s AND last_post_id = %s",
            (user_id, post_id),
        )
        return cur.fetchone() is not None
