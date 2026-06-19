"""Billing API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from db.queries.users import User
from web.auth.deps import get_current_user
from web.billing import stripe_service
from web.config import get_settings

router = APIRouter(prefix="/api/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    platform: str = Field(..., pattern="^(tiktok|threads)$")
    interval: str = Field(..., pattern="^(month|year)$")


@router.get("/plans")
def billing_plans() -> dict:
    return {"plans": stripe_service.get_plans()}


@router.post("/checkout")
def billing_checkout(body: CheckoutRequest, user: User = Depends(get_current_user)) -> dict:
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Платежи временно недоступны")
    try:
        url = stripe_service.create_checkout_session(
            user_id=user.id,
            email=user.email,
            name=user.name,
            stripe_customer_id=user.stripe_customer_id,
            platform=body.platform,
            interval=body.interval,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"checkout_url": url}


@router.post("/portal")
def billing_portal(user: User = Depends(get_current_user)) -> dict:
    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="Нет активных подписок в Stripe")
    try:
        url = stripe_service.create_portal_session(user.stripe_customer_id)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"portal_url": url}


@router.post("/webhook")
async def billing_webhook(request: Request) -> dict:
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        stripe_service.handle_webhook(payload, sig)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"received": True}
