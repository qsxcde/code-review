import unittest

from app.schemas.review import (
    ReviewMetrics,
    ReviewPRInfo,
    ReviewResult,
    ReviewSuggestion,
    ReviewSummary,
    RiskItem as ReviewRiskItem,
)


class AggregatorMergeTests(unittest.TestCase):
    def _make_risk(self, file: str, line: int, severity: str, issue: str) -> ReviewRiskItem:
        return ReviewRiskItem(
            file=file, line=line, severity=severity,
            category="test", issue=issue, impact="impact",
            suggestion="fix", confidence=0.8,
        )

    def _make_result(self, risks: list, suggestions: list | None = None) -> ReviewResult:
        return ReviewResult(
            summary=ReviewSummary(overview="test", changedModules=[], impact=[]),
            risks=risks,
            suggestions=suggestions or [],
            metrics=ReviewMetrics(highRiskCount=0, mediumRiskCount=0, lowRiskCount=0, analyzedFileCount=1),
            warnings=[],
        )

    def _make_pr_info(self) -> ReviewPRInfo:
        return ReviewPRInfo(
            title="test", url="https://example.com", author="test",
            owner="o", repo="r", number=1,
            baseBranch="main", headBranch="feat",
            changedFiles=1, additions=1, deletions=1,
        )

    def test_merge_deduplicates_same_file_line_category(self):
        from app.agents.review.aggregator import merge_results

        r1 = self._make_result([
            self._make_risk("a.py", 1, "high", "[安全] SQL injection"),
        ])
        r2 = self._make_result([
            self._make_risk("a.py", 1, "high", "[安全] SQL injection"),
        ])

        merged = merge_results(
            [("[安全]", r1), ("[安全]", r2)],
            self._make_pr_info(), 100,
        )

        self.assertEqual(len(merged.analysis.risks), 1)

    def test_merge_keeps_different_lines(self):
        from app.agents.review.aggregator import merge_results

        r1 = self._make_result([
            self._make_risk("a.py", 1, "high", "[安全] issue 1"),
        ])
        r2 = self._make_result([
            self._make_risk("a.py", 2, "high", "[安全] issue 2"),
        ])

        merged = merge_results(
            [("[安全]", r1), ("[安全]", r2)],
            self._make_pr_info(), 100,
        )

        self.assertEqual(len(merged.analysis.risks), 2)

    def test_merge_recomputes_metrics(self):
        from app.agents.review.aggregator import merge_results

        r1 = self._make_result([
            self._make_risk("a.py", 1, "high", "[安全] R1"),
            self._make_risk("b.py", 1, "medium", "[安全] R2"),
        ])
        r2 = self._make_result([
            self._make_risk("c.py", 1, "low", "[性能] R3"),
        ])

        merged = merge_results(
            [("[安全]", r1), ("[性能]", r2)],
            self._make_pr_info(), 100,
        )

        m = merged.analysis.metrics
        self.assertEqual(m.highRiskCount, 1)
        self.assertEqual(m.mediumRiskCount, 1)
        self.assertEqual(m.lowRiskCount, 1)

    def test_detect_conflicts_same_file_line_different_severity(self):
        from app.agents.review.aggregator import detect_conflicts

        risks = [
            self._make_risk("a.py", 42, "high", "[安全] critical"),
            self._make_risk("a.py", 42, "low", "[性能] minor"),
        ]

        conflicts = detect_conflicts(risks)
        self.assertGreater(len(conflicts), 0)
        self.assertEqual(conflicts[0]["file"], "a.py")
        self.assertEqual(conflicts[0]["line"], 42)


if __name__ == "__main__":
    unittest.main()
