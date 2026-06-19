"""Session token storage."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from db.connection import get_connection


def create_session(user_id: UUID, token_hash: str, expires_at: datetime) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO sessions (user_id, token_hash, expires_at)
            VALUES (%s, %s, %s)
            """,
            (user_id, token_hash, expires_at),
        )
        conn.commit()


def get_session_user_id(token_hash: str) -> UUID | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT user_id FROM sessions
            WHERE token_hash = %s AND expires_at > NOW()
            """,
            (token_hash,),
        )
        row = cur.fetchone()
        return row[0] if row else None


def delete_session(token_hash: str) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM sessions WHERE token_hash = %s", (token_hash,))
        conn.commit()
