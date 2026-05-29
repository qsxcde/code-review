import json
import unittest

from app.services.llm.parser import parse_review_result


class LLMParserTests(unittest.TestCase):
    def test_parse_review_result_from_fenced_json(self) -> None:
        payload = {
            "summary": {
                "overview": "没有发现明确风险",
                "changedModules": ["backend"],
                "impact": ["低"],
            },
            "risks": [],
            "suggestions": [],
            "metrics": {
                "highRiskCount": 0,
                "mediumRiskCount": 0,
                "lowRiskCount": 0,
                "analyzedFileCount": 1,
            },
            "warnings": [],
        }
        content = f"```json\n{json.dumps(payload, ensure_ascii=False)}\n```"

        result = parse_review_result(content)

        self.assertEqual(result.summary.overview, "没有发现明确风险")
        self.assertEqual(result.metrics.analyzedFileCount, 1)


if __name__ == "__main__":
    unittest.main()
