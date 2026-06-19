"""User session and saved post bookmarks (canonical data lives in posts/comments)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from db.connection import get_connection
from db.queries.posts import (
    SUMMARY_COLUMNS,
    get_post_summary,
    load_inspect_payload,
    post_exists,
    post_summary_from_row,
    user_can_view_post,
    user_has_saved_post,
)


def _summary_to_dict(summary) -> dict[str, Any]:
    return {
        "id": summary.post_id,
        "platform": summary.platform,
        "post_url": summary.post_url,
        "post_id": summary.post_id,
        "author_name": summary.author_name,
        "author_username": summary.author_username,
        "author_avatar_url": summary.author_avatar_url,
        "description_preview": summary.description_preview,
        "views": summary.views,
        "likes": summary.likes,
        "comments_count": summary.comments_count,
        "shares_count": summary.shares_count,
        "is_saved": summary.is_saved,
        "analyzed_at": summary.scraped_at.isoformat(),
        "saved_at": summary.saved_at.isoformat() if summary.saved_at else None,
    }


def _detail_from_post_id(post_id: str, *, is_saved: bool, platform: str = "tiktok") -> dict[str, Any] | None:
    summary = get_post_summary(post_id, is_saved=is_saved)
    payload = load_inspect_payload(post_id, platform=platform)
    if not summary or not payload:
        return None
    return {**_summary_to_dict(summary), "payload": payload}


def create_session(user_id: UUID, raw: dict[str, Any]) -> str:
    post_id = raw.get("item", {}).get("post_id")
    if not post_id:
        raise ValueError("post_id missing from analyze result")
    if not post_exists(post_id):
        raise ValueError(f"Post {post_id} not found in database")

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET last_post_id = %s WHERE id = %s",
            (post_id, user_id),
        )
        conn.commit()
    return post_id


def get_last_session(user_id: UUID) -> dict[str, Any] | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT last_post_id, last_post_id = ANY(saved_post_ids)
            FROM users
            WHERE id = %s AND last_post_id IS NOT NULL
            """,
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        post_id, is_saved = row
        return _detail_from_post_id(post_id, is_saved=bool(is_saved))


def dismiss_last_session(user_id: UUID) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET last_post_id = NULL WHERE id = %s",
            (user_id,),
        )
        conn.commit()


def get_user_post(user_id: UUID, post_id: str) -> dict[str, Any] | None:
    if not user_can_view_post(user_id, post_id):
        return None
    is_saved = user_has_saved_post(user_id, post_id)
    return _detail_from_post_id(post_id, is_saved=is_saved)


def bookmark_post(user_id: UUID, post_id: str) -> dict[str, Any] | None:
    if not post_exists(post_id):
        return None
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE users
            SET saved_post_ids = array_prepend(%s::text, array_remove(saved_post_ids, %s::text)),
                last_post_id = NULL
            WHERE id = %s
            """,
            (post_id, post_id, user_id),
        )
        if cur.rowcount == 0:
            conn.commit()
            return None
        conn.commit()
    summary = get_post_summary(post_id, is_saved=True)
    return _summary_to_dict(summary) if summary else None


def list_saved(user_id: UUID, limit: int = 50) -> list[dict[str, Any]]:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {SUMMARY_COLUMNS}
            FROM users u
            CROSS JOIN unnest(u.saved_post_ids) WITH ORDINALITY AS sp(post_id, ord)
            JOIN posts p ON p.post_id = sp.post_id
            JOIN authors a ON a.tiktok_id = p.author_id
            WHERE u.id = %s
            ORDER BY sp.ord
            LIMIT %s
            """,
            (user_id, limit),
        )
        return [
            _summary_to_dict(post_summary_from_row(row, is_saved=True, saved_at=None))
            for row in cur.fetchall()
        ]


def delete_saved(user_id: UUID, post_id: str) -> bool:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE users
            SET saved_post_ids = array_remove(saved_post_ids, %s::text)
            WHERE id = %s AND %s::text = ANY(saved_post_ids)
            """,
            (post_id, user_id, post_id),
        )
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted
