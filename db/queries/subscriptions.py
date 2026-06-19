"""Platform subscription queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from db.connection import get_connection


@dataclass(slots=True)
class PlatformSubscription:
    id: UUID
    user_id: UUID
    platform: str
    billing_interval: str
    status: str
    stripe_subscription_id: str | None
    stripe_price_id: str | None
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    created_at: datetime


_SUB_COLUMNS = """
    id, user_id, platform, billing_interval, status,
    stripe_subscription_id, stripe_price_id,
    current_period_start, current_period_end, cancel_at_period_end, created_at
"""


def _row_to_sub(row: tuple[Any, ...]) -> PlatformSubscription:
    return PlatformSubscription(
        id=row[0],
        user_id=row[1],
        platform=row[2],
        billing_interval=row[3],
        status=row[4],
        stripe_subscription_id=row[5],
        stripe_price_id=row[6],
        current_period_start=row[7],
        current_period_end=row[8],
        cancel_at_period_end=row[9],
        created_at=row[10],
    )


def get_active_subscriptions(user_id: UUID) -> list[PlatformSubscription]:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT {_SUB_COLUMNS}
            FROM platform_subscriptions
            WHERE user_id = %s AND status = 'active'
            ORDER BY platform
            """,
            (user_id,),
        )
        return [_row_to_sub(row) for row in cur.fetchall()]


def user_has_active_platform(user_id: UUID, platform: str) -> bool:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM platform_subscriptions
            WHERE user_id = %s AND platform = %s AND status = 'active'
            LIMIT 1
            """,
            (user_id, platform),
        )
        return cur.fetchone() is not None


def upsert_subscription(
    *,
    user_id: UUID,
    platform: str,
    billing_interval: str,
    status: str,
    stripe_subscription_id: str | None,
    stripe_price_id: str | None,
    current_period_start: datetime | None,
    current_period_end: datetime | None,
    cancel_at_period_end: bool,
) -> PlatformSubscription:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO platform_subscriptions (
                user_id, platform, billing_interval, status,
                stripe_subscription_id, stripe_price_id,
                current_period_start, current_period_end, cancel_at_period_end
            ) VALUES (%s, %s, %s::billing_interval, %s::subscription_status, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, platform) DO UPDATE SET
                billing_interval = EXCLUDED.billing_interval,
                status = EXCLUDED.status,
                stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                stripe_price_id = EXCLUDED.stripe_price_id,
                current_period_start = EXCLUDED.current_period_start,
                current_period_end = EXCLUDED.current_period_end,
                cancel_at_period_end = EXCLUDED.cancel_at_period_end
            RETURNING {_SUB_COLUMNS}
            """,
            (
                user_id,
                platform,
                billing_interval,
                status,
                stripe_subscription_id,
                stripe_price_id,
                current_period_start,
                current_period_end,
                cancel_at_period_end,
            ),
        )
        row = cur.fetchone()
        conn.commit()
        return _row_to_sub(row)


def get_subscription_by_stripe_id(stripe_subscription_id: str) -> PlatformSubscription | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT {_SUB_COLUMNS} FROM platform_subscriptions WHERE stripe_subscription_id = %s",
            (stripe_subscription_id,),
        )
        row = cur.fetchone()
        return _row_to_sub(row) if row else None


def count_active_by_platform() -> dict[str, int]:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT platform, COUNT(*) FROM platform_subscriptions
            WHERE status = 'active'
            GROUP BY platform
            """
        )
        return {row[0]: int(row[1]) for row in cur.fetchall()}


def count_active_subscriptions() -> int:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM platform_subscriptions WHERE status = 'active'")
        return int(cur.fetchone()[0])


def list_recent_subscriptions(limit: int = 20) -> list[dict[str, Any]]:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT ps.platform, ps.billing_interval, ps.status, ps.created_at,
                   u.email, u.name
            FROM platform_subscriptions ps
            JOIN users u ON u.id = ps.user_id
            ORDER BY ps.created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()
        return [
            {
                "platform": r[0],
                "billing_interval": r[1],
                "status": r[2],
                "created_at": r[3].isoformat() if r[3] else None,
                "user_email": r[4],
                "user_name": r[5],
            }
            for r in rows
        ]
