"""Persist parsed TikTok data to PostgreSQL."""

from __future__ import annotations

from typing import TYPE_CHECKING

import psycopg

if TYPE_CHECKING:
    from platforms.tiktok.parsers.author import ParsedAuthor
    from platforms.tiktok.parsers.comments import ParsedComment, ParsedCommentUser
    from platforms.tiktok.parsers.hashtags import ParsedHashtag
    from platforms.tiktok.parsers.item import ParsedItem
    from platforms.tiktok.parsers.music import ParsedMusic


def upsert_author(conn: psycopg.Connection, author: ParsedAuthor) -> None:
    conn.execute(
        """
        INSERT INTO authors (
            tiktok_id, unique_id, nickname, avatar_larger, create_time, verified,
            follower_count, following_count, heart, heart_count, video_count, digg_count, updated_at
        ) VALUES (
            %(tiktok_id)s, %(unique_id)s, %(nickname)s, %(avatar_larger)s, %(create_time)s, %(verified)s,
            %(follower_count)s, %(following_count)s, %(heart)s, %(heart_count)s, %(video_count)s, %(digg_count)s, NOW()
        )
        ON CONFLICT (tiktok_id) DO UPDATE SET
            unique_id = EXCLUDED.unique_id,
            nickname = EXCLUDED.nickname,
            avatar_larger = EXCLUDED.avatar_larger,
            create_time = EXCLUDED.create_time,
            verified = EXCLUDED.verified,
            follower_count = EXCLUDED.follower_count,
            following_count = EXCLUDED.following_count,
            heart = EXCLUDED.heart,
            heart_count = EXCLUDED.heart_count,
            video_count = EXCLUDED.video_count,
            digg_count = EXCLUDED.digg_count,
            updated_at = NOW()
        """,
        {
            "tiktok_id": author.tiktok_id,
            "unique_id": author.unique_id,
            "nickname": author.nickname,
            "avatar_larger": author.avatar_larger,
            "create_time": author.create_time,
            "verified": author.verified,
            "follower_count": author.follower_count,
            "following_count": author.following_count,
            "heart": author.heart,
            "heart_count": author.heart_count,
            "video_count": author.video_count,
            "digg_count": author.digg_count,
        },
    )


def upsert_music(conn: psycopg.Connection, music: ParsedMusic) -> None:
    conn.execute(
        """
        INSERT INTO music (
            music_id, title, play_url, cover_large, author_name, original, duration, updated_at
        ) VALUES (
            %(music_id)s, %(title)s, %(play_url)s, %(cover_large)s, %(author_name)s, %(original)s, %(duration)s, NOW()
        )
        ON CONFLICT (music_id) DO UPDATE SET
            title = EXCLUDED.title,
            play_url = EXCLUDED.play_url,
            cover_large = EXCLUDED.cover_large,
            author_name = EXCLUDED.author_name,
            original = EXCLUDED.original,
            duration = EXCLUDED.duration,
            updated_at = NOW()
        """,
        {
            "music_id": music.music_id,
            "title": music.title,
            "play_url": music.play_url,
            "cover_large": music.cover_large,
            "author_name": music.author_name,
            "original": music.original,
            "duration": music.duration,
        },
    )


def upsert_post(
    conn: psycopg.Connection,
    clean_url: str,
    item: ParsedItem,
) -> None:
    cover_url = item.media.video_cover if item.media else None
    photo_urls = item.media.photo_urls if item.media else None

    conn.execute(
        """
        INSERT INTO posts (
            post_id, content_type, url, author_id, music_id, description, description_preview,
            description_length, description_keywords,
            location_created, diversification_labels, cover_url, photo_urls,
            play_count, digg_count, comment_count, share_count, collect_count, scraped_at
        ) VALUES (
            %(post_id)s, %(content_type)s, %(url)s, %(author_id)s, %(music_id)s, %(description)s, %(description_preview)s,
            %(description_length)s, %(description_keywords)s,
            %(location_created)s, %(diversification_labels)s, %(cover_url)s, %(photo_urls)s,
            %(play_count)s, %(digg_count)s, %(comment_count)s, %(share_count)s, %(collect_count)s, NOW()
        )
        ON CONFLICT (post_id) DO UPDATE SET
            content_type = EXCLUDED.content_type,
            url = EXCLUDED.url,
            author_id = EXCLUDED.author_id,
            music_id = EXCLUDED.music_id,
            description = EXCLUDED.description,
            description_preview = EXCLUDED.description_preview,
            description_length = EXCLUDED.description_length,
            description_keywords = EXCLUDED.description_keywords,
            location_created = EXCLUDED.location_created,
            diversification_labels = EXCLUDED.diversification_labels,
            cover_url = EXCLUDED.cover_url,
            photo_urls = EXCLUDED.photo_urls,
            play_count = EXCLUDED.play_count,
            digg_count = EXCLUDED.digg_count,
            comment_count = EXCLUDED.comment_count,
            share_count = EXCLUDED.share_count,
            collect_count = EXCLUDED.collect_count,
            scraped_at = NOW()
        """,
        {
            "post_id": item.post_id,
            "content_type": item.content_type,
            "url": clean_url,
            "author_id": item.author.tiktok_id,
            "music_id": item.music.music_id if item.music else None,
            "description": item.description,
            "description_preview": item.description_preview,
            "description_length": item.description_length,
            "description_keywords": item.description_keywords or None,
            "location_created": item.location_created,
            "diversification_labels": item.diversification_labels or None,
            "cover_url": cover_url,
            "photo_urls": photo_urls,
            "play_count": item.metrics.views,
            "digg_count": item.metrics.likes,
            "comment_count": item.metrics.comments,
            "share_count": item.metrics.shares,
            "collect_count": item.metrics.saves,
        },
    )


def replace_post_hashtags(
    conn: psycopg.Connection,
    post_id: str,
    hashtags: list[ParsedHashtag],
) -> None:
    conn.execute("DELETE FROM post_hashtags WHERE post_id = %s", (post_id,))

    for tag in hashtags:
        conn.execute(
            """
            INSERT INTO hashtags (hashtag_id, name)
            VALUES (%(hashtag_id)s, %(name)s)
            ON CONFLICT (hashtag_id) DO UPDATE SET name = EXCLUDED.name
            """,
            {"hashtag_id": tag.hashtag_id, "name": tag.name},
        )
        conn.execute(
            """
            INSERT INTO post_hashtags (post_id, hashtag_id, start_pos, end_pos)
            VALUES (%(post_id)s, %(hashtag_id)s, %(start_pos)s, %(end_pos)s)
            ON CONFLICT (post_id, start_pos, end_pos) DO UPDATE SET
                hashtag_id = EXCLUDED.hashtag_id
            """,
            {
                "post_id": post_id,
                "hashtag_id": tag.hashtag_id,
                "start_pos": tag.start_pos,
                "end_pos": tag.end_pos,
            },
        )


def upsert_author_from_comment(conn: psycopg.Connection, user: ParsedCommentUser) -> None:
    unique_id = user.unique_id or user.uid
    conn.execute(
        """
        INSERT INTO authors (tiktok_id, unique_id, nickname, updated_at)
        VALUES (%(tiktok_id)s, %(unique_id)s, %(nickname)s, NOW())
        ON CONFLICT (tiktok_id) DO UPDATE SET
            nickname = COALESCE(EXCLUDED.nickname, authors.nickname),
            unique_id = COALESCE(NULLIF(EXCLUDED.unique_id, ''), authors.unique_id),
            updated_at = NOW()
        """,
        {
            "tiktok_id": user.uid,
            "unique_id": unique_id,
            "nickname": user.nickname,
        },
    )


def _insert_comment(conn: psycopg.Connection, comment: ParsedComment) -> None:
    conn.execute(
        """
        INSERT INTO comments (
            comment_id, post_id, parent_comment_id, is_reply, text, create_time,
            comment_language, digg_count, is_author_digged, reply_comment_total,
            author_id, scraped_at
        ) VALUES (
            %(comment_id)s, %(post_id)s, %(parent_comment_id)s, %(is_reply)s, %(text)s, %(create_time)s,
            %(comment_language)s, %(digg_count)s, %(is_author_digged)s, %(reply_comment_total)s,
            %(author_id)s, NOW()
        )
        ON CONFLICT (comment_id) DO UPDATE SET
            post_id = EXCLUDED.post_id,
            parent_comment_id = EXCLUDED.parent_comment_id,
            is_reply = EXCLUDED.is_reply,
            text = EXCLUDED.text,
            create_time = EXCLUDED.create_time,
            comment_language = EXCLUDED.comment_language,
            digg_count = EXCLUDED.digg_count,
            is_author_digged = EXCLUDED.is_author_digged,
            reply_comment_total = EXCLUDED.reply_comment_total,
            author_id = EXCLUDED.author_id,
            scraped_at = NOW()
        """,
        {
            "comment_id": comment.comment_id,
            "post_id": comment.post_id,
            "parent_comment_id": comment.parent_comment_id,
            "is_reply": comment.is_reply,
            "text": comment.text,
            "create_time": comment.create_time,
            "comment_language": comment.comment_language,
            "digg_count": comment.digg_count,
            "is_author_digged": comment.is_author_digged,
            "reply_comment_total": comment.reply_comment_total,
            "author_id": comment.user.uid,
        },
    )


def replace_post_comments(
    conn: psycopg.Connection,
    post_id: str,
    comments: list[ParsedComment],
) -> None:
    conn.execute("DELETE FROM comments WHERE post_id = %s", (post_id,))

    users_seen: set[str] = set()
    for comment in comments:
        if comment.user.uid not in users_seen:
            upsert_author_from_comment(conn, comment.user)
            users_seen.add(comment.user.uid)

    for comment in comments:
        if not comment.is_reply:
            _insert_comment(conn, comment)
    for comment in comments:
        if comment.is_reply:
            _insert_comment(conn, comment)


def save_post(clean_url: str, item: ParsedItem, comments: list[ParsedComment]) -> None:
    from db.connection import get_connection

    with get_connection() as conn:
        with conn.transaction():
            upsert_author(conn, item.author)
            if item.music:
                upsert_music(conn, item.music)
            upsert_post(conn, clean_url, item)
            replace_post_hashtags(conn, item.post_id, item.hashtags)
            replace_post_comments(conn, item.post_id, comments)
