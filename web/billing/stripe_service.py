"""Stripe billing service."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import stripe

from db.queries.payments import record_payment_event
from db.queries.subscriptions import get_subscription_by_stripe_id, upsert_subscription
from db.queries.users import get_user_by_id, set_stripe_customer_id
from web.config import Settings, get_settings

logger = logging.getLogger(__name__)

PLATFORM_FROM_METADATA = ("tiktok", "threads")


def _init_stripe(settings: Settings | None = None) -> Settings:
    s = settings or get_settings()
    if not s.stripe_secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY не настроен")
    stripe.api_key = s.stripe_secret_key
    return s


def get_plans(settings: Settings | None = None) -> list[dict[str, Any]]:
    s = settings or get_settings()
    from platforms.registry import PLATFORMS

    plans = []
    for platform in PLATFORMS:
        price_ids = s.stripe_prices.get(platform.id.value, {})
        plans.append(
            {
                "platform": platform.id.value,
                "name": platform.name,
                "available": platform.available,
                "prices": {
                    "month": {
                        "amount_cents": s.monthly_price_cents,
                        "currency": "usd",
                        "stripe_price_id": price_ids.get("month"),
                    },
                    "year": {
                        "amount_cents": s.yearly_price_cents,
                        "currency": "usd",
                        "stripe_price_id": price_ids.get("year"),
                    },
                },
            }
        )
    return plans


def _ensure_customer(user_id: UUID, email: str, name: str | None, existing_customer_id: str | None) -> str:
    if existing_customer_id:
        return existing_customer_id
    customer = stripe.Customer.create(email=email, name=name or email, metadata={"user_id": str(user_id)})
    set_stripe_customer_id(user_id, customer.id)
    return customer.id


def create_checkout_session(
    *,
    user_id: UUID,
    email: str,
    name: str | None,
    stripe_customer_id: str | None,
    platform: str,
    interval: str,
) -> str:
    s = _init_stripe()
    if platform not in PLATFORM_FROM_METADATA:
        raise ValueError("Неизвестная платформа")
    if interval not in ("month", "year"):
        raise ValueError("Интервал должен быть month или year")

    price_id = s.stripe_prices.get(platform, {}).get(interval)
    if not price_id:
        raise RuntimeError(f"Stripe price не настроен для {platform}/{interval}")

    customer_id = _ensure_customer(user_id, email, name, stripe_customer_id)
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{s.frontend_url}/billing?success=1",
        cancel_url=f"{s.frontend_url}/billing?canceled=1",
        metadata={"user_id": str(user_id), "platform": platform, "interval": interval},
        subscription_data={"metadata": {"user_id": str(user_id), "platform": platform, "interval": interval}},
    )
    return session.url


def create_portal_session(stripe_customer_id: str) -> str:
    s = _init_stripe()
    if not stripe_customer_id:
        raise ValueError("Нет Stripe customer")
    session = stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=f"{s.frontend_url}/billing",
    )
    return session.url


def _ts_to_dt(ts: int | None) -> datetime | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _sync_subscription(stripe_sub: dict[str, Any], user_id: UUID | None = None) -> None:
    meta = stripe_sub.get("metadata") or {}
    platform = meta.get("platform")
    interval = meta.get("interval", "month")
    uid = user_id or (UUID(meta["user_id"]) if meta.get("user_id") else None)

    if not uid or not platform:
        existing = get_subscription_by_stripe_id(stripe_sub["id"])
        if existing:
            uid = existing.user_id
            platform = existing.platform
            interval = existing.billing_interval
        else:
            logger.warning("Cannot sync subscription %s: missing metadata", stripe_sub.get("id"))
            return

    status_map = {
        "active": "active",
        "canceled": "canceled",
        "past_due": "past_due",
        "trialing": "trialing",
        "incomplete": "incomplete",
        "unpaid": "past_due",
    }
    raw_status = stripe_sub.get("status", "incomplete")
    status = status_map.get(raw_status, "incomplete")

    items = stripe_sub.get("items", {}).get("data", [])
    price_id = items[0]["price"]["id"] if items else None
    if items and items[0]["price"].get("recurring", {}).get("interval") == "year":
        interval = "year"
    elif items and items[0]["price"].get("recurring", {}).get("interval") == "month":
        interval = "month"

    upsert_subscription(
        user_id=uid,
        platform=platform,
        billing_interval=interval,
        status=status,
        stripe_subscription_id=stripe_sub["id"],
        stripe_price_id=price_id,
        current_period_start=_ts_to_dt(stripe_sub.get("current_period_start")),
        current_period_end=_ts_to_dt(stripe_sub.get("current_period_end")),
        cancel_at_period_end=bool(stripe_sub.get("cancel_at_period_end")),
    )


def handle_webhook(payload: bytes, sig_header: str) -> None:
    s = _init_stripe()
    if not s.stripe_webhook_secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET не настроен")

    event = stripe.Webhook.construct_event(payload, sig_header, s.stripe_webhook_secret)
    data = event["data"]["object"]
    user_id = None
    amount_cents = None

    if event["type"] == "checkout.session.completed":
        meta = data.get("metadata") or {}
        if meta.get("user_id"):
            user_id = UUID(meta["user_id"])
        sub_id = data.get("subscription")
        if sub_id:
            stripe_sub = stripe.Subscription.retrieve(sub_id)
            _sync_subscription(stripe_sub, user_id)

    elif event["type"] in ("customer.subscription.updated", "customer.subscription.deleted"):
        _sync_subscription(data)

    elif event["type"] == "invoice.paid":
        amount_cents = data.get("amount_paid")
        customer_id = data.get("customer")
        if customer_id:
            from db.connection import get_connection

            with get_connection() as conn, conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE stripe_customer_id = %s", (customer_id,))
                row = cur.fetchone()
                if row:
                    user_id = row[0]

    record_payment_event(
        stripe_event_id=event["id"],
        event_type=event["type"],
        user_id=user_id,
        amount_cents=amount_cents,
        currency=data.get("currency", "usd") if isinstance(data, dict) else "usd",
        payload=event,
    )
