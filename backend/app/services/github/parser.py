import re

from fastapi import HTTPException, status

GITHUB_PR_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)(?:[/?#].*)?$"
)


def parse_pr_url(url: str) -> tuple[str, str, int]:
    match = GITHUB_PR_URL_RE.match(url)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid GitHub PR URL",
        )

    return (
        match.group("owner"),
        match.group("repo"),
        int(match.group("number")),
    )
