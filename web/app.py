"""FastAPI application for the video inspector UI."""

from __future__ import annotations

import asyncio
import logging
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from web.fetch_worker import fetch_video_job
from web.serialize import platforms_list

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Social Lead Monitor", version="0.1.0")

_pool: ProcessPoolExecutor | None = None


def _get_pool() -> ProcessPoolExecutor:
    global _pool
    if _pool is None:
        kwargs: dict = {"max_workers": 1}
        if sys.version_info >= (3, 11):
            kwargs["max_tasks_per_child"] = 1
        _pool = ProcessPoolExecutor(**kwargs)
    return _pool


class FetchRequest(BaseModel):
    url: str = Field(..., min_length=8, description="Post URL")
    show_browser: bool = Field(False, description="Show Chromium window during fetch")


@app.on_event("shutdown")
async def shutdown() -> None:
    global _pool
    if _pool is not None:
        _pool.shutdown(wait=False, cancel_futures=True)
        _pool = None


@app.get("/api/platforms")
def get_platforms() -> dict:
    return {"platforms": platforms_list()}


@app.post("/api/fetch")
async def post_fetch(body: FetchRequest) -> dict:
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL не может быть пустым")

    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(
            _get_pool(),
            fetch_video_job,
            url,
            body.show_browser,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Fetch failed for %s", url)
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки: {exc}") from exc


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
