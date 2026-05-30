import re
from typing import Any

from app.schemas.github import GitHubPR, GitHubPRFile

SKIPPED_FILE_SUFFIXES = (
    ".lock",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".pdf",
    ".zip",
)
SKIPPED_FILE_PARTS = (
    "/dist/",
    "/build/",
    "/node_modules/",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
)
MAX_FILES_FOR_CONTEXT = 30
MAX_PATCH_CHARS = 6000


class ReviewContextBuilder:
    def build(self, pr_data: GitHubPR) -> tuple[dict[str, Any], int]:
        files = self.select_files(pr_data.files)
        context = {
            "prUrl": pr_data.html_url,
            "title": pr_data.title,
            "description": pr_data.body,
            "author": pr_data.author,
            "baseBranch": pr_data.base_branch,
            "headBranch": pr_data.head_branch,
            "changedFiles": pr_data.changed_files,
            "additions": pr_data.additions,
            "deletions": pr_data.deletions,
            "files": files,
            "contextNotes": self._build_context_notes(pr_data.files),
        }
        return context, len(files)

    def select_files(self, files: list[GitHubPRFile]) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []

        for file in files:
            if len(selected) >= MAX_FILES_FOR_CONTEXT:
                break
            if self.should_skip_file(file.filename) or not file.patch:
                continue

            patch = file.patch
            truncated = len(patch) > MAX_PATCH_CHARS
            selected.append(
                {
                    "filename": file.filename,
                    "status": file.status,
                    "additions": file.additions,
                    "deletions": file.deletions,
                    "changes": file.changes,
                    "patch": patch[:MAX_PATCH_CHARS],
                    "truncated": truncated,
                }
            )

        return selected

    def should_skip_file(self, filename: str) -> bool:
        normalized_filename = filename.replace("\\", "/")
        normalized = f"/{normalized_filename}"
        return normalized.endswith(SKIPPED_FILE_SUFFIXES) or any(
            part in normalized for part in SKIPPED_FILE_PARTS
        )

    def has_truncated_patch(self, files: list[GitHubPRFile]) -> bool:
        return any(file.patch and len(file.patch) > MAX_PATCH_CHARS for file in files)

    def _build_context_notes(self, files: list[GitHubPRFile]) -> list[str]:
        notes = [
            "过大的 patch 已被截断。" if self.has_truncated_patch(files) else "",
            "lock 文件、构建产物和二进制资源默认不送入模型。",
        ]
        return [note for note in notes if note]

    def build_filtered(
        self, pr_data, agents
    ) -> dict[str, dict[str, Any]]:
        """Build filtered contexts for multiple specialist agents.

        Returns a dict mapping agent name to context payload.
        """
        contexts: dict[str, dict[str, Any]] = {}
        for agent in agents:
            selected = self._select_files_for_agent(pr_data.files, agent)
            context, count = self._build_from_selected(selected)
            contexts[agent.name] = context
        return contexts

    def _select_files_for_agent(self, files, agent) -> list:
        """Select files matching the agent's filter policy."""
        skip_patterns = [
            r"\.json$", r"\.lock$", r"\.yml$", r"\.yaml$",
            r"\.md$", r"\.svg$", r"\.png$", r"\.css$",
        ]
        selected = []
        for f in files:
            if not f.patch:
                continue
            filename = f.filename.lower()
            if any(re.search(p, filename) for p in skip_patterns):
                continue
            if "test" in filename:
                continue
            if agent.include_pattern and not re.search(
                agent.include_pattern, filename
            ):
                continue
            if len(selected) >= agent.max_files:
                break
            selected.append(f)
        return selected

    def _build_from_selected(
        self, files: list
    ) -> tuple[dict[str, Any], int]:
        """Build context from pre-selected files list."""
        analyzed_count = len(files)
        file_patches = []
        for f in files:
            patch = f.patch or ""
            truncated = len(patch) > MAX_PATCH_CHARS
            if truncated:
                patch = patch[:MAX_PATCH_CHARS]
            file_patches.append({
                "filename": f.filename,
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
                "patch": patch,
                "truncated": truncated,
            })
        return {
            "files": file_patches,
            "file_count": analyzed_count,
        }, analyzed_count
