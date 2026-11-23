"""FastAPI application factory with middleware, lifespan, error handling, and routing."""

from __future__ import annotations

import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import auth, chat, conversations, health, pages, personas
from app.core.config import get_settings
from app.core.logging import get_logger, request_id_ctx, setup_logging
from app.core.rate_limit import SlidingWindowRateLimiter
from app.db.database import init_db
from app.services.model_registry import ModelError

BASE_DIR = Path(__file__).resolve().parent.parent
logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()
    setup_logging(settings.log_level)

    rate_limiter = SlidingWindowRateLimiter(
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        init_db()
        logger.info(
            "Starting %s v%s (env=%s)",
            settings.app_name,
            settings.app_version,
            settings.environment,
        )
        yield
        logger.info("Shutting down %s", settings.app_name)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="多模型智能聊天助手：支持真实流式对话、多会话持久化、联网搜索引用、多模态理解与绘图、自定义角色。",
        lifespan=lifespan,
    )

    # Expose rate limiter on app state so tests can reset/inspect it
    app.state.rate_limiter = rate_limiter

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context_and_rate_limit(request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        token = request_id_ctx.set(req_id)
        start = time.perf_counter()

        try:
            path = request.url.path
            is_api_call = path.startswith("/api/") or path in ("/chat", "/generate_image")
            is_exempt = path == "/api/health" or request.method == "OPTIONS"

            if settings.rate_limit_enabled and is_api_call and not is_exempt:
                client_ip = request.client.host if request.client else "unknown"
                guest_id = request.headers.get("X-Guest-ID", "")
                rate_key = f"{client_ip}:{guest_id[:24]}"
                allowed, remaining, retry_after = rate_limiter.allow(rate_key)
                if not allowed:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": "请求过于频繁，请稍后再试。",
                            "code": "RATE_LIMIT_EXCEEDED",
                            "retry_after": retry_after,
                        },
                        headers={
                            "Retry-After": str(retry_after),
                            "X-Request-ID": req_id,
                            "X-RateLimit-Remaining": "0",
                        },
                    )
            else:
                remaining = None

            response = await call_next(request)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            response.headers["X-Request-ID"] = req_id
            response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
            if remaining is not None:
                response.headers["X-RateLimit-Remaining"] = str(remaining)
            return response
        finally:
            request_id_ctx.reset(token)

    @app.exception_handler(ModelError)
    async def handle_model_error(_request: Request, exc: ModelError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, exc: Exception):
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "服务器内部错误，请稍后重试。", "code": "INTERNAL_SERVER_ERROR"},
        )

    # Mount static directories if present
    static_dir = BASE_DIR / "static"
    img_dir = BASE_DIR / "img"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    if img_dir.exists():
        app.mount("/img", StaticFiles(directory=str(img_dir)), name="img")

    # Register route modules
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(personas.router)
    app.include_router(conversations.router)
    app.include_router(chat.router)
    app.include_router(pages.router)

    # Vercel Python serverless adapters may invoke ASGI without running lifespan first
    if os.getenv("VERCEL"):
        init_db()

    return app


app = create_app()
