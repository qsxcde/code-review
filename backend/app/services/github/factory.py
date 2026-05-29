from app.services.github.service import GitHubPRService

_github_services: dict[tuple[str | None, str | None], GitHubPRService] = {}


def get_github_pr_service(
    token: str | None = None,
    proxy: str | None = None,
) -> GitHubPRService:
    key = (token, proxy)
    if key not in _github_services:
        _github_services[key] = GitHubPRService(token=token, proxy=proxy)
    return _github_services[key]


async def close_github_pr_services() -> None:
    for service in _github_services.values():
        await service.aclose()
    _github_services.clear()
