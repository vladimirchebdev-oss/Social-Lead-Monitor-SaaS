"""Auth dependencies for FastAPI routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, Request, status

from db.queries.users import User, get_user_by_id
from web.auth.jwt_utils import decode_access_token


def get_current_user(
    request: Request,
    access_token: str | None = Cookie(default=None, alias="access_token"),
) -> User:
    token = access_token
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется авторизация")

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен")

    user = get_user_by_id(UUID(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")

    request.state.user = user
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ только для администратора")
    return user
