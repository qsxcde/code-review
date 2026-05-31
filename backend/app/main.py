import logging
import time
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.services.github import close_github_pr_services

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    configure_logging(settings.log_level, settings.log_format)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.on_event("startup")
    async def startup_services() -> None:
        from app.core.redis import get_redis

        try:
            await get_redis()
        except Exception:
            logger.warning("Redis 连接失败，部分功能（速率限制、热缓存）将降级运行", exc_info=True)

    @app.on_event("shutdown")
    async def shutdown_services() -> None:
        import asyncio

        from app.core.redis import close_redis

        await close_github_pr_services()
        await close_redis()

        try:
            from app.core.db import engine

            await engine.dispose()
        except Exception:
            pass

    @app.middleware("http")
    async def log_requests(request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        started_at = time.perf_counter()
        client_host = request.client.host if request.client else "unknown"

        logger.info(
            "请求开始",
            extra={"props": {"request_id": request_id, "method": request.method, "path": request.url.path}},
        )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.exception(
                "请求异常",
                extra={"props": {"request_id": request_id, "method": request.method, "path": request.url.path, "duration": f"{duration_ms:.0f}ms"}},
            )
            raise

        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "请求完成",
            extra={"props": {"request_id": request_id, "method": request.method, "path": request.url.path, "status": response.status_code, "duration": f"{duration_ms:.0f}ms"}},
        )
        return response

    return app


app = create_app()
