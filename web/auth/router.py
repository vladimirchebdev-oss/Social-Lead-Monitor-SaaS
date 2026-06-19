"""Authentication API routes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from authlib.integrations.base_client.errors import MismatchingStateError
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from starlette.requests import Request as StarletteRequest

from db.queries.sessions import create_session, delete_session, get_session_user_id
from db.queries.subscriptions import get_active_subscriptions
from db.queries.users import User, get_user_by_id, upsert_oauth_user
from web.auth.deps import get_current_user
from web.auth.jwt_utils import (
    create_access_token,
    create_csrf_token,
    create_refresh_token,
    hash_token,
)
from web.auth.oauth import oauth
from web.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _oauth_redirect_uri(request: StarletteRequest) -> str:
    return str(request.url_for("oauth_callback"))


def _dashboard_url(request: StarletteRequest) -> str:
    settings = get_settings()
    backend = urlparse(str(request.base_url))
    frontend = urlparse(settings.frontend_url)
    if backend.hostname == frontend.hostname:
        return f"{settings.frontend_url.rstrip('/')}/dashboard"
    return f"{str(request.base_url).rstrip('/')}/dashboard"


def _set_auth_cookies(response: Response, user: User, refresh_token: str) -> str:
    settings = get_settings()
    access = create_access_token(user.id, user.role)
    csrf = create_csrf_token()

    response.set_cookie(
        "access_token",
        access,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
        path="/api/auth",
    )
    response.set_cookie(
        "csrf_token",
        csrf,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
        path="/",
    )
    return csrf


def _create_session_for_user(user: User) -> str:
    refresh = create_refresh_token()
    expires = datetime.now(timezone.utc) + timedelta(days=get_settings().refresh_token_expire_days)
    create_session(user.id, hash_token(refresh), expires)
    return refresh


@router.get("/providers")
def list_providers(request: StarletteRequest) -> dict:
    settings = get_settings()
    providers = []
    if settings.google_client_id:
        providers.append({"id": "google", "name": "Google"})
    return {
        "providers": providers,
        "oauth_base_url": str(request.base_url).rstrip("/"),
    }


@router.get("/google")
async def auth_google(request: StarletteRequest):
    if "google" not in oauth._clients:
        raise HTTPException(status_code=503, detail="Google OAuth не настроен")
    return await oauth.google.authorize_redirect(request, _oauth_redirect_uri(request))


@router.get("/callback/google", name="oauth_callback")
async def auth_callback_google(request: StarletteRequest):
    settings = get_settings()
    if "google" not in oauth._clients:
        raise HTTPException(status_code=503, detail="Google OAuth не настроен")

    try:
        token = await oauth.google.authorize_access_token(request)
    except MismatchingStateError:
        login_url = f"{settings.frontend_url.rstrip('/')}/login?error=oauth_state"
        return RedirectResponse(url=login_url, status_code=302)

    userinfo = token.get("userinfo")
    if not userinfo:
        userinfo = await oauth.google.parse_id_token(request, token)

    email = userinfo.get("email")
    name = userinfo.get("name")
    avatar = userinfo.get("picture")
    provider_user_id = userinfo.get("sub")

    if not email or not provider_user_id:
        raise HTTPException(status_code=400, detail="Не удалось получить email от Google")

    user = upsert_oauth_user(
        provider="google",
        provider_user_id=provider_user_id,
        email=email,
        name=name,
        avatar_url=avatar,
        admin_email=settings.admin_email,
    )

    refresh = _create_session_for_user(user)
    redirect = RedirectResponse(url=_dashboard_url(request), status_code=302)
    _set_auth_cookies(redirect, user, refresh)
    return redirect


@router.get("/me")
def auth_me(user: User = Depends(get_current_user)) -> dict:
    subs = get_active_subscriptions(user.id)
    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "role": user.role,
        },
        "subscriptions": [
            {
                "platform": s.platform,
                "billing_interval": s.billing_interval,
                "status": s.status,
                "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
            }
            for s in subs
        ],
    }


@router.post("/refresh")
def auth_refresh(
    response: Response,
    request: Request,
    refresh_token: str | None = Cookie(default=None, alias="refresh_token"),
) -> dict:
    rt = refresh_token or request.cookies.get("refresh_token")
    if not rt:
        raise HTTPException(status_code=401, detail="Нет активной сессии")

    user_id = get_session_user_id(hash_token(rt))
    if not user_id:
        raise HTTPException(status_code=401, detail="Сессия истекла")

    user = get_user_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    delete_session(hash_token(rt))
    new_refresh = _create_session_for_user(user)
    csrf = _set_auth_cookies(response, user, new_refresh)
    return {"ok": True, "csrf_token": csrf}


@router.post("/logout")
def auth_logout(
    response: Response,
    request: Request,
    refresh_token: str | None = Cookie(default=None, alias="refresh_token"),
):
    rt = refresh_token or request.cookies.get("refresh_token")
    if rt:
        delete_session(hash_token(rt))

    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/auth")
    response.delete_cookie("csrf_token", path="/")
    return {"ok": True}


@router.get("/csrf")
def get_csrf(request: Request) -> dict:
    token = request.cookies.get("csrf_token")
    if not token:
        raise HTTPException(status_code=401, detail="Нет активной сессии")
    return {"csrf_token": token}
