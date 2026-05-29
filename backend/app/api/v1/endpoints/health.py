from fastapi import APIRouter, Depends, Response, status

from app.core.config import Settings, get_settings
from app.schemas.health import HealthCheck, ReadinessCheck
from app.services.health import build_readiness_dependencies

router = APIRouter()


@router.get("/health", response_model=HealthCheck)
async def health_check() -> HealthCheck:
    return HealthCheck(status="ok")


@router.get("/ready", response_model=ReadinessCheck)
async def readiness_check(
    response: Response,
    check_external: bool = False,
    settings: Settings = Depends(get_settings),
) -> ReadinessCheck:
    dependencies = await build_readiness_dependencies(settings, check_external=check_external)
    is_ready = all(item.status in {"ok", "skipped"} for item in dependencies)
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessCheck(
        status="ok" if is_ready else "degraded",
        dependencies=dependencies,
    )
