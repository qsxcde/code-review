from app.schemas.review import ReviewMetrics, ReviewResult


class ReviewResultNormalizer:
    def normalize(
        self,
        analysis: ReviewResult,
        analyzed_file_count: int,
    ) -> ReviewResult:
        warnings = list(analysis.warnings)
        risks = []
        low_confidence_filtered_count = 0
        missing_file_high_risk_count = 0

        for risk in analysis.risks:
            if risk.confidence < 0.5:
                low_confidence_filtered_count += 1
                continue

            if risk.severity == "high" and not risk.file:
                missing_file_high_risk_count += 1
                risks.append(risk.model_copy(update={"file": "unknown"}))
                continue

            risks.append(risk)

        if low_confidence_filtered_count:
            warnings.append(
                f"已过滤 {low_confidence_filtered_count} 个置信度低于 50% 的风险项。"
            )
        if missing_file_high_risk_count:
            warnings.append(
                f"已保留 {missing_file_high_risk_count} 个缺少文件定位的高风险项，并将文件标记为 unknown。"
            )

        suggestions_by_key = {}
        for suggestion in analysis.suggestions:
            key = (suggestion.file, suggestion.type, suggestion.comment)
            suggestions_by_key[key] = suggestion

        metrics = ReviewMetrics(
            highRiskCount=sum(1 for risk in risks if risk.severity == "high"),
            mediumRiskCount=sum(1 for risk in risks if risk.severity == "medium"),
            lowRiskCount=sum(1 for risk in risks if risk.severity == "low"),
            analyzedFileCount=analyzed_file_count,
        )

        return ReviewResult(
            summary=analysis.summary,
            risks=risks,
            suggestions=list(suggestions_by_key.values()),
            metrics=metrics,
            warnings=warnings,
        )
