"""Tests for feedback_service helpers: _extract_agent, _parse_risk."""

import unittest
from unittest.mock import MagicMock

from app.services.review.feedback_service import _extract_agent, _parse_risk


class ExtractAgentTests(unittest.TestCase):
    def test_parses_security_prefix(self) -> None:
        self.assertEqual(_extract_agent("[安全] SQL injection risk"), "安全")

    def test_parses_performance_prefix(self) -> None:
        self.assertEqual(_extract_agent("[性能] N+1 query detected"), "性能")

    def test_parses_style_prefix(self) -> None:
        self.assertEqual(_extract_agent("[风格] Variable naming issue"), "风格")

    def test_defaults_to_generic_when_no_prefix(self) -> None:
        self.assertEqual(_extract_agent("Some random issue"), "通用")

    def test_handles_empty_string(self) -> None:
        self.assertEqual(_extract_agent(""), "通用")

    def test_handles_bracket_without_known_agent(self) -> None:
        self.assertEqual(_extract_agent("[未知] unknown issue"), "通用")


class ParseRiskTests(unittest.TestCase):
    def test_extracts_risk_at_valid_index(self) -> None:
        record = MagicMock()
        record.result_json = {
            "analysis": {
                "risks": [
                    {"file": "a.py", "issue": "first"},
                    {"file": "b.py", "issue": "second"},
                ]
            }
        }
        risk = _parse_risk(record, 1)
        self.assertEqual(risk["file"], "b.py")  # type: ignore[index]

    def test_returns_none_for_out_of_range_index(self) -> None:
        record = MagicMock()
        record.result_json = {"analysis": {"risks": [{"file": "a.py"}]}}
        self.assertIsNone(_parse_risk(record, 5))

    def test_returns_none_for_none_result_json(self) -> None:
        record = MagicMock()
        record.result_json = None
        self.assertIsNone(_parse_risk(record, 0))

    def test_returns_none_for_missing_analysis_key(self) -> None:
        record = MagicMock()
        record.result_json = {"other": "data"}
        self.assertIsNone(_parse_risk(record, 0))

    def test_returns_none_for_malformed_json(self) -> None:
        record = MagicMock()
        record.result_json = "not a dict"
        self.assertIsNone(_parse_risk(record, 0))


if __name__ == "__main__":
    unittest.main()
