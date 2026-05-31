"""Tests for _merge_incremental in ReviewAnalysisService."""

import unittest

from app.schemas.review import (
    ReviewAnalyzeResponse,
    ReviewMetrics,
    ReviewPRInfo,
    ReviewResult,
    ReviewSummary,
    RiskItem,
)
from app.services.review.analysis_service import ReviewAnalysisService


def _make_risk(file: str, severity: str = "high", issue: str = "test") -> RiskItem:
    return RiskItem(
        file=file,
        severity=severity,  # type: ignore[arg-type]
        category="security",
        issue=issue,
        impact="impact",
        suggestion="suggestion",
        confidence=0.9,
    )


def _make_response(risks: list[RiskItem], analysis_mode: str = "single") -> ReviewAnalyzeResponse:
    return ReviewAnalyzeResponse(
        pr=ReviewPRInfo(
            title="Test PR",
            url="https://github.com/org/repo/pull/1",
            author="dev",
            owner="org",
            repo="repo",
            number=1,
            baseBranch="main",
            headBranch="feat",
            changedFiles=len(risks),
            additions=10,
            deletions=5,
        ),
        analysis=ReviewResult(
            summary=ReviewSummary(overview="test", changedModules=[], impact=[]),
            risks=risks,
            suggestions=[],
            metrics=ReviewMetrics(
                highRiskCount=sum(1 for r in risks if r.severity == "high"),
                mediumRiskCount=sum(1 for r in risks if r.severity == "medium"),
                lowRiskCount=sum(1 for r in risks if r.severity == "low"),
                analyzedFileCount=len(risks),
            ),
        ),
        durationMs=100,
        analysis_mode=analysis_mode,  # type: ignore[arg-type]
    )


class MergeIncrementalTests(unittest.TestCase):
    def test_keeps_unchanged_file_risks(self) -> None:
        previous = _make_response([_make_risk("auth.py", "high")])
        new = _make_response([_make_risk("payment.py", "medium")])

        changed_files = [{"filename": "payment.py"}]
        svc = _make_service()
        merged = svc._merge_incremental(new, previous, changed_files)

        self.assertEqual(merged.analysis_type, "incremental")
        self.assertEqual(len(merged.analysis.risks), 2)
        filenames = {r.file for r in merged.analysis.risks}
        self.assertIn("auth.py", filenames)  # unchanged, kept
        self.assertIn("payment.py", filenames)  # changed, new risk

    def test_replaces_changed_file_risks(self) -> None:
        previous = _make_response([_make_risk("api.py", "high", "old issue")])
        new = _make_response([_make_risk("api.py", "medium", "new issue")])

        changed_files = [{"filename": "api.py"}]
        svc = _make_service()
        merged = svc._merge_incremental(new, previous, changed_files)

        self.assertEqual(len(merged.analysis.risks), 1)
        self.assertEqual(merged.analysis.risks[0].issue, "new issue")
        self.assertEqual(merged.analysis.risks[0].severity, "medium")

    def test_computes_risk_trend(self) -> None:
        previous = _make_response([
            _make_risk("old.py", "high"),   # unchanged
            _make_risk("fixed.py", "low"),   # changed → fixed
        ])
        new = _make_response([
            _make_risk("new.py", "high"),    # new risk
        ])

        changed_files = [{"filename": "fixed.py"}, {"filename": "new.py"}]
        svc = _make_service()
        merged = svc._merge_incremental(new, previous, changed_files)

        self.assertIsNotNone(merged.risk_trend)
        self.assertEqual(merged.risk_trend.new, 1)  # type: ignore[union-attr]
        self.assertEqual(merged.risk_trend.fixed, 1)  # type: ignore[union-attr]
        self.assertEqual(merged.risk_trend.unchanged, 1)  # type: ignore[union-attr]

    def test_recomputes_metrics(self) -> None:
        previous = _make_response([_make_risk("keep.py", "high")])
        new = _make_response([_make_risk("change.py", "low")])

        changed_files = [{"filename": "change.py"}]
        svc = _make_service()
        merged = svc._merge_incremental(new, previous, changed_files)

        self.assertEqual(merged.analysis.metrics.highRiskCount, 1)  # from keep.py
        self.assertEqual(merged.analysis.metrics.lowRiskCount, 1)   # from change.py
        self.assertEqual(merged.analysis.metrics.mediumRiskCount, 0)

    def test_empty_changed_files_treats_all_as_unchanged(self) -> None:
        previous = _make_response([_make_risk("a.py"), _make_risk("b.py")])
        new = _make_response([])

        svc = _make_service()
        merged = svc._merge_incremental(new, previous, [])

        self.assertEqual(len(merged.analysis.risks), 2)
        self.assertEqual(merged.risk_trend.new, 0)  # type: ignore[union-attr]
        self.assertEqual(merged.risk_trend.unchanged, 2)  # type: ignore[union-attr]


def _make_service() -> ReviewAnalysisService:
    """Minimal service instance for testing _merge_incremental."""
    from unittest.mock import MagicMock

    svc = ReviewAnalysisService(
        github_service=MagicMock(),
        settings=MagicMock(),
    )
    return svc


if __name__ == "__main__":
    unittest.main()
