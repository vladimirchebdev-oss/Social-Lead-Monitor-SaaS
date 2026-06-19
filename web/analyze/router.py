"""Protected analyze API."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from db.queries.analyses import create_session
from db.queries.subscriptions import user_has_active_platform
from db.queries.users import User
from platforms.registry import detect_platform
from web.auth.deps import get_current_user
from web.serialize import platforms_public_list
from web.fetch_worker import fetch_video_job
from web.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["analyze"])


class AnalyzeRequest(BaseModel):
    url: str = Field(..., min_length=8)
    show_browser: bool = Field(False)


def _get_pool():
    from web.app import get_executor

    return get_executor()


@router.get("/platforms")
def get_platforms() -> dict:
    return {"platforms": platforms_public_list()}


@router.post("/analyze")
@limiter.limit("30/hour")
@limiter.limit("5/minute")
async def post_analyze(
    request: Request,
    body: AnalyzeRequest,
    user: User = Depends(get_current_user),
) -> dict:
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL не может быть пустым")

    platform = detect_platform(url)
    if platform is None:
        raise HTTPException(status_code=400, detail="Неподдерживаемая платформа или некорректный URL")
    if not platform.available:
        raise HTTPException(status_code=400, detail=f"{platform.name} пока недоступен")

    if user.role != "admin" and not user_has_active_platform(user.id, platform.id.value):
        raise HTTPException(
            status_code=402,
            detail=f"Нужна активная подписка на {platform.name}",
        )

    show_browser = body.show_browser and user.role == "admin"

    loop = asyncio.get_running_loop()
    try:
        raw = await loop.run_in_executor(_get_pool(), fetch_video_job, url, show_browser)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Analyze failed for user %s", user.id)
        raise HTTPException(status_code=500, detail="Ошибка анализа. Попробуйте позже.") from exc

    post_id = create_session(user.id, raw)
    return {**raw, "analysis_id": post_id}
