"""Admin dashboard API."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from db.queries.payments import list_recent_payments, revenue_since_days
from db.queries.subscriptions import (
    count_active_by_platform,
    count_active_subscriptions,
    list_recent_subscriptions,
)
from db.queries.users import User, count_users, count_users_since, list_users
from web.auth.deps import require_admin
from web.config import get_settings

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _compute_mrr() -> dict:
    settings = get_settings()
    by_platform = count_active_by_platform()
    monthly_subs = 0
    yearly_subs = 0

    from db.connection import get_connection

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT billing_interval, COUNT(*) FROM platform_subscriptions
            WHERE status = 'active'
            GROUP BY billing_interval
            """
        )
        for interval, count in cur.fetchall():
            if interval == "month":
                monthly_subs = int(count)
            elif interval == "year":
                yearly_subs = int(count)

    mrr_cents = monthly_subs * settings.monthly_price_cents + yearly_subs * (settings.yearly_price_cents // 12)
    arr_cents = mrr_cents * 12
    return {
        "mrr_cents": mrr_cents,
        "arr_cents": arr_cents,
        "active_subscriptions": count_active_subscriptions(),
        "by_platform": by_platform,
        "monthly_plans": monthly_subs,
        "yearly_plans": yearly_subs,
    }


@router.get("/stats")
def admin_stats(_: User = Depends(require_admin)) -> dict:
    return {
        "users": {
            "total": count_users(),
            "new_7d": count_users_since(7),
            "new_30d": count_users_since(30),
        },
        "revenue": {
            "last_30d_cents": revenue_since_days(30),
            "last_7d_cents": revenue_since_days(7),
        },
        "subscriptions": _compute_mrr(),
        "recent_payments": list_recent_payments(15),
        "recent_subscriptions": list_recent_subscriptions(15),
    }


@router.get("/users")
def admin_users(_: User = Depends(require_admin), limit: int = 100, offset: int = 0) -> dict:
    users = list_users(limit=limit, offset=offset)
    from db.queries.subscriptions import get_active_subscriptions

    result = []
    for u in users:
        subs = get_active_subscriptions(u.id)
        result.append(
            {
                "id": str(u.id),
                "email": u.email,
                "name": u.name,
                "role": u.role,
                "created_at": u.created_at.isoformat(),
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
                "stripe_customer_id": u.stripe_customer_id,
                "platforms": [s.platform for s in subs],
            }
        )
    return {"users": result, "total": count_users()}
