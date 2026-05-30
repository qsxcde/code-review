import time
import unittest

from app.agents.review.nodes import ReviewWorkflowNodes
from app.schemas.github import GitHubPR, GitHubPRFile
from app.schemas.review import (
    ReviewMetrics,
    ReviewResult,
    ReviewSummary,
)


class _GitHubService:
    def parse_pr_url(self, _url: str) -> tuple[str, str, int]:
        return "owner", "repo", 7

    async def fetch_parsed_pr(self, _owner: str, _repo: str, _number: int) -> GitHubPR:
        return GitHubPR(
            owner="owner",
            repo="repo",
            number=7,
            title="Title",
            body="Body",
            state="open",
            author="alice",
            html_url="https://github.com/owner/repo/pull/7",
            base_branch="main",
            head_branch="feature",
            changed_files=3,
            additions=42,
            deletions=9,
            files=[
                GitHubPRFile(
                    filename="src/app.py",
                    status="modified",
                    additions=42,
                    deletions=9,
                    changes=51,
                    patch="+print('ok')",
                )
            ],
        )


class _LLMService:
    async def analyze_payload(self, _payload):
        return ReviewResult(
            summary=ReviewSummary(overview="overview", changedModules=[], impact=[]),
            risks=[],
            suggestions=[],
            metrics=ReviewMetrics(
                highRiskCount=0,
                mediumRiskCount=0,
                lowRiskCount=0,
                analyzedFileCount=0,
            ),
        )


class ReviewResponsePrStatsTests(unittest.IsolatedAsyncioTestCase):
    async def test_validate_result_includes_pr_line_statistics(self) -> None:
        nodes = ReviewWorkflowNodes(_GitHubService(), _LLMService())
        state = await nodes.fetch_pr_data(
            {
                "pr_url": "https://github.com/owner/repo/pull/7",
                "owner": "owner",
                "repo": "repo",
                "pull_number": 7,
                "started_at": time.perf_counter(),
                "errors": [],
            }
        )
        state = await nodes.build_context(state)
        state = await nodes.analyze_review(state)
        state = await nodes.validate_result(state)

        self.assertEqual(state["response"].pr.changedFiles, 3)
        self.assertEqual(state["response"].pr.additions, 42)
        self.assertEqual(state["response"].pr.deletions, 9)


if __name__ == "__main__":
    unittest.main()
