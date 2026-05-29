from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.rate_limit import require_rate_limit
from app.core.security import require_api_token
from app.schemas.github import GitHubPR, GitHubPRRequest
from app.services.github import get_github_pr_service

router = APIRouter(
    prefix="/github",
    tags=["github"],
    dependencies=[Depends(require_api_token), Depends(require_rate_limit)],
)


@router.post("/pr", response_model=GitHubPR)
async def get_github_pr(
    request: GitHubPRRequest,
    settings: Settings = Depends(get_settings),
) -> GitHubPR:
    service = get_github_pr_service(
        token=settings.github_token,
        proxy=settings.github_api_proxy,
    )
    return await service.fetch_pr(str(request.url))
