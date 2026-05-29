import unittest

from app.agents.review.context import MAX_PATCH_CHARS, ReviewContextBuilder
from app.schemas.github import GitHubPRFile


class ReviewContextBuilderTests(unittest.TestCase):
    def test_select_files_skips_generated_and_binary_files(self) -> None:
        builder = ReviewContextBuilder()
        files = [
            self._file("src/app.py", patch="+print('ok')"),
            self._file("package-lock.json", patch="+lock"),
            self._file("assets/logo.png", patch="+binary"),
            self._file("web/dist/app.js", patch="+built"),
            self._file("src/no_patch.py", patch=None),
        ]

        selected = builder.select_files(files)

        self.assertEqual([item["filename"] for item in selected], ["src/app.py"])

    def test_select_files_truncates_large_patch(self) -> None:
        builder = ReviewContextBuilder()
        patch = "+" * (MAX_PATCH_CHARS + 10)

        selected = builder.select_files([self._file("src/app.py", patch=patch)])

        self.assertEqual(len(selected[0]["patch"]), MAX_PATCH_CHARS)
        self.assertTrue(selected[0]["truncated"])

    def _file(self, filename: str, patch: str | None) -> GitHubPRFile:
        return GitHubPRFile(
            filename=filename,
            status="modified",
            additions=1,
            deletions=0,
            changes=1,
            patch=patch,
        )


if __name__ == "__main__":
    unittest.main()
