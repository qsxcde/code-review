import json
import unittest

from fastapi import HTTPException

from app.services.llm.parser import parse_json_object, parse_review_result


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

    def test_invalid_json_detail_contains_stage_and_preview(self) -> None:
        with self.assertRaises(HTTPException) as context:
            parse_review_result("not-json-response", stage="agent:security", model="deepseek-v4-pro")

        detail = context.exception.detail
        self.assertEqual(detail["code"], "llm_invalid_json")
        self.assertEqual(detail["stage"], "agent:security")
        self.assertEqual(detail["model"], "deepseek-v4-pro")
        self.assertIn("not-json-response", detail["content_preview"])

    def test_schema_error_detail_contains_stage_and_preview(self) -> None:
        with self.assertRaises(HTTPException) as context:
            parse_review_result('{"overview": "wrong shape"}', stage="phase1", model="deepseek-v4-pro")

        detail = context.exception.detail
        self.assertEqual(detail["code"], "llm_schema_invalid")
        self.assertEqual(detail["stage"], "phase1")
        self.assertEqual(detail["model"], "deepseek-v4-pro")
        self.assertGreater(detail["error_count"], 0)

    def test_parse_plain_json_object_for_orchestrator_phase(self) -> None:
        result = parse_json_object(
            '{"security_focus": "检查鉴权", "impact": ["影响订单流转"]}',
            stage="phase1",
            model="deepseek-v4-pro",
        )

        self.assertEqual(result["security_focus"], "检查鉴权")
        self.assertEqual(result["impact"], ["影响订单流转"])


if __name__ == "__main__":
    unittest.main()
