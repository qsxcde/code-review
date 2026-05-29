import unittest

from app.agents.review.normalizer import ReviewResultNormalizer
from app.schemas.review import (
    ReviewMetrics,
    ReviewResult,
    ReviewSuggestion,
    ReviewSummary,
    RiskItem,
)


class ReviewResultNormalizerTests(unittest.TestCase):
    def test_normalize_filters_low_confidence_and_recomputes_metrics(self) -> None:
        analysis = ReviewResult(
            summary=ReviewSummary(overview="概览", changedModules=["api"], impact=["低"]),
            risks=[
                RiskItem(
                    file="src/app.py",
                    severity="high",
                    category="correctness",
                    issue="问题",
                    impact="影响",
                    suggestion="建议",
                    confidence=0.9,
                ),
                RiskItem(
                    file="src/weak.py",
                    severity="medium",
                    category="test",
                    issue="弱问题",
                    impact="弱影响",
                    suggestion="弱建议",
                    confidence=0.2,
                ),
                RiskItem(
                    file="",
                    severity="high",
                    category="security",
                    issue="缺少文件",
                    impact="影响",
                    suggestion="建议",
                    confidence=0.8,
                ),
            ],
            suggestions=[
                ReviewSuggestion(file="src/app.py", type="must_fix", comment="修复"),
                ReviewSuggestion(file="src/app.py", type="must_fix", comment="修复"),
            ],
            metrics=ReviewMetrics(
                highRiskCount=0,
                mediumRiskCount=0,
                lowRiskCount=0,
                analyzedFileCount=0,
            ),
        )

        normalized = ReviewResultNormalizer().normalize(analysis, analyzed_file_count=3)

        self.assertEqual(len(normalized.risks), 2)
        self.assertEqual(normalized.risks[1].file, "unknown")
        self.assertEqual(len(normalized.suggestions), 1)
        self.assertEqual(normalized.metrics.highRiskCount, 2)
        self.assertEqual(normalized.metrics.mediumRiskCount, 0)
        self.assertEqual(normalized.metrics.analyzedFileCount, 3)
        self.assertEqual(len(normalized.warnings), 2)


if __name__ == "__main__":
    unittest.main()
