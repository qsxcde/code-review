import unittest
from unittest.mock import MagicMock

from app.schemas.github import GitHubPR, GitHubPRFile


class OrchestratorRoutingTests(unittest.TestCase):
    def _make_pr(self, changed_files: int, additions: int, deletions: int) -> GitHubPR:
        return GitHubPR(
            owner="test", repo="test", number=1,
            title="test", state="open", author="test",
            html_url="https://github.com/test/test/pull/1",
            base_branch="main", head_branch="feat",
            changed_files=changed_files, additions=additions,
            deletions=deletions, files=[], head_sha="abc",
        )

    def test_small_pr_uses_single(self):
        from app.agents.review.orchestrator import _should_use_multi_agent

        pr = self._make_pr(changed_files=2, additions=120, deletions=80)
        self.assertFalse(_should_use_multi_agent(pr))

    def test_large_pr_uses_multi(self):
        from app.agents.review.orchestrator import _should_use_multi_agent

        pr = self._make_pr(changed_files=15, additions=200, deletions=100)
        self.assertTrue(_should_use_multi_agent(pr))

    def test_many_lines_uses_multi(self):
        from app.agents.review.orchestrator import _should_use_multi_agent

        pr = self._make_pr(changed_files=5, additions=4000, deletions=2000)
        self.assertTrue(_should_use_multi_agent(pr))

    def test_middle_ground_uses_single(self):
        from app.agents.review.orchestrator import _should_use_multi_agent

        pr = self._make_pr(changed_files=3, additions=400, deletions=200)
        self.assertFalse(_should_use_multi_agent(pr))

    def test_exact_boundary_uses_single(self):
        from app.agents.review.orchestrator import _should_use_multi_agent

        pr = self._make_pr(changed_files=2, additions=150, deletions=150)
        self.assertFalse(_should_use_multi_agent(pr))


if __name__ == "__main__":
    unittest.main()
