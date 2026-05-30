import unittest

from app.agents.review.truncator import detect_language, smart_truncate


class SmartTruncateTests(unittest.TestCase):
    def test_short_content_passes_through(self):
        short = "def foo():\n    pass\n"
        result = smart_truncate(short, max_chars=100, language="py")
        self.assertEqual(result, short)

    def test_python_truncates_at_function_boundary(self):
        content = "import os\n\n\ndef foo():\n    pass\n\n\ndef bar():\n    return 1\n"
        # make it long by repeating
        long_content = content * 50
        self.assertGreater(len(long_content), 100)

        result = smart_truncate(long_content, max_chars=100, language="py")
        self.assertLess(len(result), len(long_content))
        self.assertIn("# ... (truncated)", result)

    def test_fallback_when_no_boundary(self):
        content = "x" * 5000
        result = smart_truncate(content, max_chars=100, language="py")
        self.assertEqual(len(result), 100 + len("\n# ... (truncated)"))

    def test_detect_language_python(self):
        self.assertEqual(detect_language("src/main.py"), "py")

    def test_detect_language_typescript(self):
        self.assertEqual(detect_language("components/App.tsx"), "ts")

    def test_detect_language_unknown(self):
        self.assertEqual(detect_language("README.md"), "")


if __name__ == "__main__":
    unittest.main()
