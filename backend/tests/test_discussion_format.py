"""Tests for _format_discussion in orchestrator."""

import unittest

from app.agents.review.orchestrator import _format_discussion
from app.schemas.github import PRComment, PRDiscussion


def _make_comment(author: str, body: str, created_at: str = "2026-01-01T00:00:00Z") -> PRComment:
    return PRComment(author=author, body=body, created_at=created_at)


class FormatDiscussionTests(unittest.TestCase):
    def test_returns_empty_for_none(self) -> None:
        self.assertEqual(_format_discussion(None), "")

    def test_returns_pr_body_only_when_no_comments(self) -> None:
        disc = PRDiscussion(
            pr_body="This PR adds retry logic.",
            issue_comments=[],
            review_comments=[],
        )
        result = _format_discussion(disc)
        self.assertIn("[PR 描述] This PR adds retry logic.", result)
        self.assertNotIn("[author]", result)

    def test_includes_comments_sorted_by_recency(self) -> None:
        disc = PRDiscussion(
            pr_body="",
            issue_comments=[
                _make_comment("alice", "LGTM", "2026-01-02T00:00:00Z"),
                _make_comment("bob", "Please check auth", "2026-01-01T00:00:00Z"),
            ],
            review_comments=[],
        )
        result = _format_discussion(disc)
        # newest first: alice before bob
        alice_pos = result.index("alice")
        bob_pos = result.index("bob")
        self.assertLess(alice_pos, bob_pos)

    def test_truncates_long_comment_bodies(self) -> None:
        long_body = "x" * 500
        disc = PRDiscussion(
            pr_body=None,
            issue_comments=[_make_comment("dev", long_body)],
            review_comments=[],
        )
        result = _format_discussion(disc)
        self.assertLessEqual(len(result), 3000)  # should be well under cap
        self.assertIn("[dev]", result)

    def test_caps_total_output(self) -> None:
        comments = [
            _make_comment(f"user{i}", f"Comment number {i}" * 20, f"2026-01-{i + 1:02d}T00:00:00Z")
            for i in range(20)
        ]
        disc = PRDiscussion(
            pr_body="A" * 2000,
            issue_comments=comments,
            review_comments=[],
        )
        result = _format_discussion(disc)
        # DISCUSSION_MAX_CHARS = 2000, should truncate
        self.assertLessEqual(len(result), 2100)
        self.assertIn("(discussion truncated)", result)

    def test_merges_issue_and_review_comments(self) -> None:
        disc = PRDiscussion(
            pr_body="",
            issue_comments=[_make_comment("a", "issue comment")],
            review_comments=[_make_comment("b", "review comment")],
        )
        result = _format_discussion(disc)
        self.assertIn("issue comment", result)
        self.assertIn("review comment", result)

    def test_replaces_newlines_in_comments(self) -> None:
        disc = PRDiscussion(
            pr_body="",
            issue_comments=[_make_comment("dev", "line1\nline2\nline3")],
            review_comments=[],
        )
        result = _format_discussion(disc)
        self.assertNotIn("\nline2", result)


if __name__ == "__main__":
    unittest.main()
