from typing import Any

from app.schemas.github import GitHubPR, GitHubPRFile


def map_github_pr_response(
    owner: str,
    repo: str,
    number: int,
    pr_data: dict[str, Any],
    files_data: list[dict[str, Any]],
) -> GitHubPR:
    return GitHubPR(
        owner=owner,
        repo=repo,
        number=number,
        title=pr_data["title"],
        body=pr_data.get("body"),
        state=pr_data["state"],
        author=pr_data["user"]["login"],
        html_url=pr_data["html_url"],
        base_branch=pr_data["base"]["ref"],
        head_branch=pr_data["head"]["ref"],
        changed_files=pr_data["changed_files"],
        additions=pr_data["additions"],
        deletions=pr_data["deletions"],
        files=[
            GitHubPRFile(
                filename=file_data["filename"],
                status=file_data["status"],
                additions=file_data["additions"],
                deletions=file_data["deletions"],
                changes=file_data["changes"],
                patch=file_data.get("patch"),
            )
            for file_data in files_data
        ],
    )
