import httpx
from fastapi import status

from app.core.config import Settings
from app.schemas.health import DependencyCheck


async def build_readiness_dependencies(
    settings: Settings,
    check_external: bool = False,
) -> list[DependencyCheck]:
    dependencies = [
        check_review_auth(settings),
        check_llm_configuration(settings),
    ]

    if check_external:
        dependencies.append(await check_github_api(settings))
    else:
        dependencies.append(
            DependencyCheck(
                name="github_api",
                status="skipped",
                detail="Set check_external=true to probe GitHub API connectivity",
            )
        )

    return dependencies


def check_review_auth(settings: Settings) -> DependencyCheck:
    if settings.review_api_token:
        return DependencyCheck(name="review_api_token", status="ok")
    return DependencyCheck(
        name="review_api_token",
        status="error",
        detail="REVIEW_API_TOKEN is not configured",
    )


def check_llm_configuration(settings: Settings) -> DependencyCheck:
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


async def check_github_api(settings: Settings) -> DependencyCheck:
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

    detail = github_rate_limit_detail(response)
    return DependencyCheck(name="github_api", status="ok", detail=detail)


def github_rate_limit_detail(response: httpx.Response) -> str | None:
    remaining = response.headers.get("x-ratelimit-remaining")
    reset = response.headers.get("x-ratelimit-reset")
    if remaining is None:
        return None
    detail = f"remaining={remaining}"
    if reset:
        detail = f"{detail}, reset={reset}"
    return detail
