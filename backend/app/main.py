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
            from app.core.db import ensure_review_rule_table

            await ensure_review_rule_table()
        except Exception:
            logger.warning("Review rule table initialization failed", exc_info=True)

        try:
            await get_redis()
        except Exception:
            logger.warning(
                "Redis connection failed; related features will run in degraded mode",
                exc_info=True,
            )

        if settings.debug:
            _run_startup_tests(logger)

    def _run_startup_tests(log: logging.Logger) -> None:
        import subprocess
        import threading
        from pathlib import Path

        test_dir = Path(__file__).resolve().parent.parent / "tests"

        def _runner() -> None:
            try:
                result = subprocess.run(
                    ["python", "-m", "pytest", str(test_dir), "-q", "--tb=short"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=str(test_dir.parent),
                )
                output = result.stdout.strip() + "\n" + result.stderr.strip()
                summary = next(
                    (
                        line.strip()
                        for line in output.splitlines()
                        if "passed" in line or "failed" in line or "error" in line
                    ),
                    "",
                )

                if result.returncode == 0:
                    log.info("Startup tests passed | %s", summary)
                    return

                log.warning("Startup tests failed | %s", summary)
                for line in output.splitlines():
                    if "FAILED" in line or "ERROR" in line or "assert" in line:
                        log.warning("  %s", line.strip())
            except subprocess.TimeoutExpired:
                log.warning("Startup tests timed out")
            except Exception:
                log.warning("Startup tests failed unexpectedly", exc_info=True)

        threading.Thread(target=_runner, daemon=True).start()

    @app.on_event("shutdown")
    async def shutdown_services() -> None:
        from app.core.redis import close_redis

        await close_github_pr_services()
        await close_redis()

        try:
            from app.core.db import engine

            await engine.dispose()
        except Exception:
            logger.debug("Database engine disposal failed", exc_info=True)

    @app.middleware("http")
    async def log_requests(request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        started_at = time.perf_counter()
        client_host = request.client.host if request.client else "unknown"
        query_params = dict(request.query_params)

        request_props: dict[str, object] = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client": client_host,
        }
        if query_params:
            request_props["query"] = query_params

        logger.info("Request started", extra={"props": request_props})

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.exception(
                "Request failed",
                extra={
                    "props": {
                        **request_props,
                        "duration_ms": duration_ms,
                    }
                },
            )
            raise

        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "Request completed",
            extra={
                "props": {
                    **request_props,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                }
            },
        )
        return response

    logging.getLogger("app").info(
        "Application configured",
        extra={
            "props": {
                "name": settings.app_name,
                "version": settings.app_version,
                "debug": settings.debug,
                "api_prefix": settings.api_v1_prefix,
            }
        },
    )

    return app


app = create_app()
