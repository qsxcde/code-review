import unittest

from app.agents.review.import_parser import parse_imports


class ImportParserTests(unittest.TestCase):
    def test_python_local_imports(self):
        content = "import os\nimport sys\nfrom app.utils import foo\nfrom .models import User\n"
        result = parse_imports(content, "py")
        self.assertIn("app.utils", result)
        self.assertIn(".models", result)

    def test_filters_stdlib(self):
        content = "import os\nimport json\nimport logging\n"
        result = parse_imports(content, "py")
        self.assertEqual(len(result), 0)

    def test_js_relative_imports(self):
        content = "import React from 'react'\nimport { foo } from './utils'\nimport bar from '../bar'\n"
        result = parse_imports(content, "js")
        self.assertIn("./utils", result)
        self.assertIn("../bar", result)

    def test_unknown_language_returns_empty(self):
        content = "some content\n"
        result = parse_imports(content, "unknown")
        self.assertEqual(len(result), 0)

    def test_empty_content(self):
        result = parse_imports("", "py")
        self.assertEqual(len(result), 0)


if __name__ == "__main__":
    unittest.main()
