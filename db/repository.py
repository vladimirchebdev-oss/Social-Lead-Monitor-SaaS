"""Persist parsed TikTok data to PostgreSQL."""

from __future__ import annotations

from typing import TYPE_CHECKING

import psycopg

if TYPE_CHECKING:
    from parsers.tiktok.author import ParsedAuthor
    from parsers.tiktok.hashtags import ParsedHashtag
    from parsers.tiktok.item import ParsedVideoItem
    from parsers.tiktok.music import ParsedMusic
    from parsers.tiktok.url import ParsedUrl


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
    parsed_url: ParsedUrl,
    item: ParsedVideoItem,
) -> None:
    conn.execute(
        """
        INSERT INTO posts (
            post_id, content_type, url, author_id, music_id, description, description_preview, comments,
            location_created, diversification_labels,
            play_count, digg_count, comment_count, share_count, collect_count, scraped_at
        ) VALUES (
            %(post_id)s, %(content_type)s, %(url)s, %(author_id)s, %(music_id)s, NULL, %(description_preview)s, NULL,
            %(location_created)s, %(diversification_labels)s,
            %(play_count)s, %(digg_count)s, %(comment_count)s, %(share_count)s, %(collect_count)s, NOW()
        )
        ON CONFLICT (post_id) DO UPDATE SET
            content_type = EXCLUDED.content_type,
            url = EXCLUDED.url,
            author_id = EXCLUDED.author_id,
            music_id = EXCLUDED.music_id,
            description_preview = EXCLUDED.description_preview,
            location_created = EXCLUDED.location_created,
            diversification_labels = EXCLUDED.diversification_labels,
            play_count = EXCLUDED.play_count,
            digg_count = EXCLUDED.digg_count,
            comment_count = EXCLUDED.comment_count,
            share_count = EXCLUDED.share_count,
            collect_count = EXCLUDED.collect_count,
            scraped_at = NOW()
        """,
        {
            "post_id": parsed_url.post_id,
            "content_type": parsed_url.content_type,
            "url": parsed_url.clean_url,
            "author_id": item.author.tiktok_id,
            "music_id": item.music.music_id if item.music else None,
            "description_preview": item.description_preview,
            "location_created": item.location_created,
            "diversification_labels": item.diversification_labels or None,
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


def save_video_post(parsed_url: ParsedUrl, item: ParsedVideoItem) -> None:
    from db.connection import get_connection

    with get_connection() as conn:
        with conn.transaction():
            upsert_author(conn, item.author)
            if item.music:
                upsert_music(conn, item.music)
            upsert_post(conn, parsed_url, item)
            replace_post_hashtags(conn, parsed_url.post_id, item.hashtags)
