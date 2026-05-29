import httpx
from fastapi import APIRouter, Depends, Response, status

from app.core.config import Settings, get_settings
from app.schemas.health import DependencyCheck, HealthCheck, ReadinessCheck

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
    dependencies = [
        _check_review_auth(settings),
        _check_llm_configuration(settings),
    ]

    if check_external:
        dependencies.append(await _check_github_api(settings))
    else:
        dependencies.append(
            DependencyCheck(
                name="github_api",
                status="skipped",
                detail="Set check_external=true to probe GitHub API connectivity",
            )
        )

    is_ready = all(item.status in {"ok", "skipped"} for item in dependencies)
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessCheck(
        status="ok" if is_ready else "degraded",
        dependencies=dependencies,
    )


def _check_review_auth(settings: Settings) -> DependencyCheck:
    if settings.review_api_token:
        return DependencyCheck(name="review_api_token", status="ok")
    return DependencyCheck(
        name="review_api_token",
        status="error",
        detail="REVIEW_API_TOKEN is not configured",
    )


def _check_llm_configuration(settings: Settings) -> DependencyCheck:
    if not settings.openai_api_key or not settings.openai_model:
        return DependencyCheck(
            name="llm_configuration",
            status="error",
            detail="OPENAI_API_KEY and OPENAI_MODEL are required",
        )

    try:
        from langchain_core.prompts import ChatPromptTemplate  # noqa: F401
        from langchain_openai import ChatOpenAI  # noqa: F401
    except ImportError as exc:
        return DependencyCheck(
            name="llm_configuration",
            status="error",
            detail=f"LLM dependency import failed: {exc.__class__.__name__}",
        )

    return DependencyCheck(name="llm_configuration", status="ok")


async def _check_github_api(settings: Settings) -> DependencyCheck:
    headers: dict[str, str] = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ai-code-review-backend",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    try:
        async with httpx.AsyncClient(
            timeout=5,
            proxy=settings.github_api_proxy,
        ) as client:
            response = await client.get(
                "https://api.github.com/rate_limit",
                headers=headers,
            )
    except httpx.RequestError as exc:
        return DependencyCheck(
            name="github_api",
            status="error",
            detail=f"GitHub API probe failed: {exc.__class__.__name__}",
        )

    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        return DependencyCheck(
            name="github_api",
            status="error",
            detail="GitHub token is invalid",
        )

    if response.status_code >= 500:
        return DependencyCheck(
            name="github_api",
            status="error",
            detail=f"GitHub API returned {response.status_code}",
        )

    detail = _github_rate_limit_detail(response)
    return DependencyCheck(name="github_api", status="ok", detail=detail)


def _github_rate_limit_detail(response: httpx.Response) -> str | None:
    remaining = response.headers.get("x-ratelimit-remaining")
    reset = response.headers.get("x-ratelimit-reset")
    if remaining is None:
        return None
    detail = f"remaining={remaining}"
    if reset:
        detail = f"{detail}, reset={reset}"
    return detail
