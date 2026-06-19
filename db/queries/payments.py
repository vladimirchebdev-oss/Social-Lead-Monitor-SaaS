"""Payment event queries."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from db.connection import get_connection


def record_payment_event(
    *,
    stripe_event_id: str,
    event_type: str,
    user_id: UUID | None,
    amount_cents: int | None,
    currency: str,
    payload: dict[str, Any],
) -> bool:
    """Insert event if new. Returns True if inserted."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO payment_events (stripe_event_id, event_type, user_id, amount_cents, currency, payload)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (stripe_event_id) DO NOTHING
            RETURNING id
            """,
            (stripe_event_id, event_type, user_id, amount_cents, currency, json.dumps(payload)),
        )
        inserted = cur.fetchone() is not None
        conn.commit()
        return inserted


def revenue_since_days(days: int) -> int:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(SUM(amount_cents), 0)
            FROM payment_events
            WHERE created_at >= NOW() - make_interval(days => %s)
              AND event_type = 'invoice.paid'
            """,
            (days,),
        )
        return int(cur.fetchone()[0])


def list_recent_payments(limit: int = 20) -> list[dict[str, Any]]:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT pe.event_type, pe.amount_cents, pe.currency, pe.created_at,
                   u.email, u.name
            FROM payment_events pe
            LEFT JOIN users u ON u.id = pe.user_id
            ORDER BY pe.created_at DESC
            LIMIT %s
            """,
            (limit,),
        )
        return [
            {
                "event_type": r[0],
                "amount_cents": r[1],
                "currency": r[2],
                "created_at": r[3].isoformat() if r[3] else None,
                "user_email": r[4],
                "user_name": r[5],
            }
            for r in cur.fetchall()
        ]
