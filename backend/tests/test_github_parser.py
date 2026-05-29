import unittest

from fastapi import HTTPException

from app.services.github.parser import parse_pr_url


class GitHubParserTests(unittest.TestCase):
    def test_parse_valid_pr_url_with_query(self) -> None:
        owner, repo, number = parse_pr_url("https://github.com/acme/widget/pull/42?tab=files")

        self.assertEqual(owner, "acme")
        self.assertEqual(repo, "widget")
        self.assertEqual(number, 42)

    def test_parse_invalid_pr_url_raises_400(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            parse_pr_url("https://example.com/acme/widget/pull/42")

        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(raised.exception.detail, "Invalid GitHub PR URL")


if __name__ == "__main__":
    unittest.main()
