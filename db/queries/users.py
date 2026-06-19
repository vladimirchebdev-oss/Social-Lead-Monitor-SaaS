"""User and OAuth account queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from db.connection import get_connection


@dataclass(slots=True)
class User:
    id: UUID
    email: str
    name: str | None
    avatar_url: str | None
    role: str
    stripe_customer_id: str | None
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


def _row_to_user(row: tuple[Any, ...]) -> User:
    return User(
        id=row[0],
        email=row[1],
        name=row[2],
        avatar_url=row[3],
        role=row[4],
        stripe_customer_id=row[5],
        is_active=row[6],
        created_at=row[7],
        last_login_at=row[8],
    )


_USER_COLUMNS = """
    id, email, name, avatar_url, role, stripe_customer_id, is_active, created_at, last_login_at
"""


def get_user_by_id(user_id: UUID) -> User | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT {_USER_COLUMNS} FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        return _row_to_user(row) if row else None


def get_user_by_oauth(provider: str, provider_user_id: str) -> User | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT u.id, u.email, u.name, u.avatar_url, u.role, u.stripe_customer_id,
                   u.is_active, u.created_at, u.last_login_at
            FROM users u
            JOIN oauth_accounts o ON o.user_id = u.id
            WHERE o.provider = %s AND o.provider_user_id = %s
            """,
            (provider, provider_user_id),
        )
        row = cur.fetchone()
        return _row_to_user(row) if row else None


def _resolve_role(email: str, admin_email: str | None, current_role: str = "user") -> str:
    if admin_email and email.lower() == admin_email.lower():
        return "admin"
    return current_role


def upsert_oauth_user(
    *,
    provider: str,
    provider_user_id: str,
    email: str,
    name: str | None,
    avatar_url: str | None,
    admin_email: str | None,
) -> User:
    existing = get_user_by_oauth(provider, provider_user_id)
    now = datetime.utcnow()

    with get_connection() as conn, conn.cursor() as cur:
        if existing:
            role = _resolve_role(email, admin_email, existing.role)
            cur.execute(
                """
                UPDATE users
                SET name = COALESCE(%s, name),
                    avatar_url = COALESCE(%s, avatar_url),
                    role = %s::user_role,
                    last_login_at = %s
                WHERE id = %s
                RETURNING """ + _USER_COLUMNS,
                (name, avatar_url, role, now, existing.id),
            )
            conn.commit()
            return _row_to_user(cur.fetchone())

        role = _resolve_role(email, admin_email)
        cur.execute(
            """
            INSERT INTO users (email, name, avatar_url, role, last_login_at)
            VALUES (%s, %s, %s, %s::user_role, %s)
            RETURNING """ + _USER_COLUMNS,
            (email, name, avatar_url, role, now),
        )
        user = _row_to_user(cur.fetchone())
        cur.execute(
            """
            INSERT INTO oauth_accounts (user_id, provider, provider_user_id)
            VALUES (%s, %s, %s)
            """,
            (user.id, provider, provider_user_id),
        )
        conn.commit()
        return user


def set_stripe_customer_id(user_id: UUID, customer_id: str) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET stripe_customer_id = %s WHERE id = %s",
            (customer_id, user_id),
        )
        conn.commit()


def list_users(limit: int = 100, offset: int = 0) -> list[User]:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT {_USER_COLUMNS} FROM users ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset),
        )
        return [_row_to_user(row) for row in cur.fetchall()]


def count_users() -> int:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM users")
        return int(cur.fetchone()[0])


def count_users_since(days: int) -> int:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= NOW() - make_interval(days => %s)",
            (days,),
        )
        return int(cur.fetchone()[0])
