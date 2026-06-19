"""FastAPI application — SaaS API + React SPA."""

from __future__ import annotations

import asyncio
import logging
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.sessions import SessionMiddleware

from db.schema import ensure_schema
from web.admin.router import router as admin_router
from web.analyze.router import router as analyze_router
from web.analyze.saved_router import router as analyses_router
from web.auth.router import router as auth_router
from web.billing.router import router as billing_router
from web.config import get_settings
from web.limiter import limiter

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logger = logging.getLogger(__name__)
settings = get_settings()

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST = ROOT / "frontend" / "dist"

_pool: ProcessPoolExecutor | None = None


def get_executor() -> ProcessPoolExecutor:
    global _pool
    if _pool is None:
        kwargs: dict = {"max_workers": 1}
        if sys.version_info >= (3, 11):
            kwargs["max_tasks_per_child"] = 1
        _pool = ProcessPoolExecutor(**kwargs)
    return _pool


app = FastAPI(title="Social Lead Monitor", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.jwt_secret,
    same_site="lax",
    https_only=settings.cookie_secure,
)
def _cors_origins() -> list[str]:
    origins = {settings.frontend_url.rstrip("/")}
    backend = settings.backend_url.rstrip("/")
    origins.add(backend)
    # localhost and 127.0.0.1 are different cookie domains — allow both in dev
    for url in (settings.frontend_url, settings.backend_url):
        if "localhost" in url:
            origins.add(url.replace("localhost", "127.0.0.1").rstrip("/"))
        if "127.0.0.1" in url:
            origins.add(url.replace("127.0.0.1", "localhost").rstrip("/"))
    return sorted(origins)


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        path = request.url.path
        if path.startswith("/api/billing/webhook") or path.startswith("/api/auth/callback"):
            return await call_next(request)
        if path.startswith("/api/"):
            cookie_csrf = request.cookies.get("csrf_token")
            header_csrf = request.headers.get("X-CSRF-Token")
            if cookie_csrf and header_csrf and cookie_csrf != header_csrf:
                raise HTTPException(status_code=403, detail="CSRF validation failed")
    return await call_next(request)


@app.on_event("startup")
async def startup() -> None:
    try:
        if ensure_schema():
            logger.info("Database schema applied from init.sql")
    except Exception:
        logger.exception("Schema setup failed — ensure PostgreSQL is running")


@app.on_event("shutdown")
async def shutdown() -> None:
    global _pool
    if _pool is not None:
        _pool.shutdown(wait=False, cancel_futures=True)
        _pool = None


app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(analyze_router)
app.include_router(analyses_router)
app.include_router(admin_router)


def _spa_index() -> FileResponse:
    index = FRONTEND_DIST / "index.html"
    if not index.exists():
        raise HTTPException(status_code=503, detail="Frontend не собран. Запустите npm run build в frontend/")
    return FileResponse(index)


@app.get("/")
def spa_root() -> FileResponse:
    return _spa_index()


if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str) -> FileResponse:
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return _spa_index()
