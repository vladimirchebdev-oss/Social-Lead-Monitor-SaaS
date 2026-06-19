"""Saved analyses API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from db.queries.analyses import (
    bookmark_post,
    delete_saved,
    dismiss_last_session,
    get_last_session,
    get_user_post,
    list_saved,
)
from db.queries.users import User
from web.auth.deps import get_current_user

router = APIRouter(prefix="/api/v1/analyses", tags=["analyses"])


@router.get("/session")
def get_session(user: User = Depends(get_current_user)) -> dict:
    detail = get_last_session(user.id)
    if not detail:
        return {"analysis": None}
    return {"analysis": detail}


@router.post("/session/dismiss")
def dismiss_session(user: User = Depends(get_current_user)) -> dict:
    dismiss_last_session(user.id)
    return {"ok": True}


@router.get("/saved")
def get_saved_list(user: User = Depends(get_current_user)) -> dict:
    return {"items": list_saved(user.id)}


@router.get("/{post_id}")
def get_saved_detail(post_id: str, user: User = Depends(get_current_user)) -> dict:
    detail = get_user_post(user.id, post_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Анализ не найден")
    return detail


@router.post("/{post_id}/save")
def post_save(post_id: str, user: User = Depends(get_current_user)) -> dict:
    summary = bookmark_post(user.id, post_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Анализ не найден")
    return summary


@router.delete("/{post_id}")
def remove_saved(post_id: str, user: User = Depends(get_current_user)) -> dict:
    if not delete_saved(user.id, post_id):
        raise HTTPException(status_code=404, detail="Сохранённый анализ не найден")
    return {"ok": True}
