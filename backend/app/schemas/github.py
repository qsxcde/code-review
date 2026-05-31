from pydantic import BaseModel, HttpUrl


class GitHubPRRequest(BaseModel):
    url: HttpUrl


class GitHubPRFile(BaseModel):
    filename: str
    status: str
    additions: int
    deletions: int
    changes: int
    patch: str | None = None


class GitHubPR(BaseModel):
    owner: str
    repo: str
    number: int
    title: str
    body: str | None = None
    state: str
    author: str
    html_url: str
    private: bool = False
    created_at: str | None = None
    updated_at: str | None = None
    base_branch: str
    head_branch: str
    head_sha: str = ""
    changed_files: int
    additions: int
    deletions: int
    files: list[GitHubPRFile]

