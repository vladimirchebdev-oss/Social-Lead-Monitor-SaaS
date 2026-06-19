"""Application configuration from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@dataclass(frozen=True, slots=True)
class Settings:
    jwt_secret: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int
    frontend_url: str
    backend_url: str
    admin_email: str | None
    cookie_secure: bool
    is_production: bool

    google_client_id: str | None
    google_client_secret: str | None

    stripe_secret_key: str | None
    stripe_webhook_secret: str | None
    stripe_prices: dict[str, dict[str, str]]

    monthly_price_cents: int
    yearly_price_cents: int


def _price_map() -> dict[str, dict[str, str]]:
    platforms = ("tiktok", "threads")
    intervals = ("month", "year")
    result: dict[str, dict[str, str]] = {}
    for platform in platforms:
        result[platform] = {}
        for interval in intervals:
            env_key = f"STRIPE_PRICE_{platform.upper()}_{interval.upper()}"
            value = os.getenv(env_key, "").strip()
            if value:
                result[platform][interval] = value
    return result


def get_settings() -> Settings:
    return Settings(
        jwt_secret=os.getenv("JWT_SECRET", "dev-change-me-in-production"),
        jwt_algorithm="HS256",
        access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")),
        refresh_token_expire_days=int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")),
        frontend_url=os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/"),
        backend_url=os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/"),
        admin_email=os.getenv("ADMIN_EMAIL", "").strip() or None,
        cookie_secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        is_production=os.getenv("ENV", "development").lower() == "production",
        google_client_id=os.getenv("GOOGLE_CLIENT_ID"),
        google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        stripe_secret_key=os.getenv("STRIPE_SECRET_KEY"),
        stripe_webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET"),
        stripe_prices=_price_map(),
        monthly_price_cents=1500,
        yearly_price_cents=15000,
    )
