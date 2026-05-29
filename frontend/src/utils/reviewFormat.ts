import type {
  ReviewAnalyzeResponse,
  ReviewSuggestion,
  RiskItem,
  Severity,
  SuggestionType,
} from "../types/review";

export const severityLabel: Record<Severity, string> = {
  high: "高",
  medium: "中",
  low: "低",
};

export const suggestionLabel: Record<SuggestionType, string> = {
  must_fix: "必须修复",
  should_fix: "建议修复",
  nice_to_have: "可优化",
};

export function toPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function formatMs(value: number) {
  return value > 1000 ? `${(value / 1000).toFixed(1)}s` : `${value}ms`;
}

export function riskClass(severity: Severity) {
  return `risk-${severity}`;
}

export function suggestionClass(type: SuggestionType) {
  return `suggestion-${type}`;
}

export function riskTitle(risk: RiskItem) {
  return risk.line ? `${risk.file}:${risk.line}` : risk.file;
}

export function toMarkdown(data: ReviewAnalyzeResponse) {
  const risks =
    data.analysis.risks.length === 0
      ? "- 暂无明确风险"
      : data.analysis.risks
          .map(
            (risk) =>
              `- [${severityLabel[risk.severity]}] ${risk.file}${
                risk.line ? `:${risk.line}` : ""
              }：${risk.issue}\n  - 影响：${risk.impact}\n  - 建议：${risk.suggestion}\n  - 置信度：${toPercent(risk.confidence)}`,
          )
          .join("\n");

  const suggestions =
    data.analysis.suggestions.length === 0
      ? "- 暂无建议"
      : data.analysis.suggestions
          .map(
            (suggestion: ReviewSuggestion) =>
              `- [${suggestionLabel[suggestion.type]}] ${suggestion.file}：${suggestion.comment}`,
          )
          .join("\n");

  return `# AI Review 报告

## PR
- 标题：${data.pr.title}
- 地址：${data.pr.url}
- 作者：${data.pr.author}
- 分支：${data.pr.headBranch} -> ${data.pr.baseBranch}

## 总结
${data.analysis.summary.overview}

## 审计提示
${
  data.analysis.warnings.length === 0
    ? "- 暂无"
    : data.analysis.warnings.map((item) => `- ${item}`).join("\n")
}

## 影响范围
${data.analysis.summary.impact.map((item) => `- ${item}`).join("\n")}

## 风险
${risks}

## 建议
${suggestions}

## 指标
- 高风险：${data.analysis.metrics.highRiskCount}
- 中风险：${data.analysis.metrics.mediumRiskCount}
- 低风险：${data.analysis.metrics.lowRiskCount}
- 入模文件数：${data.analysis.metrics.analyzedFileCount}
- 耗时：${formatMs(data.durationMs)}
`;
}
