import type { Ref } from "vue";
import type {
  AiSuggestion,
  Issue,
  PullRequestInfo,
  ReviewAnalyzeResponse,
  RiskLevel,
  RiskStats,
  SummaryItem,
} from "../types/review";

interface ReviewReportState {
  currentAnalysis: Ref<ReviewAnalyzeResponse | null>;
  pullRequest: Ref<PullRequestInfo>;
  analyzedUrl: Ref<string>;
  riskStats: Ref<RiskStats>;
  summaryItems: Ref<SummaryItem[]>;
  topIssues: Ref<Issue[]>;
  aiSuggestions: Ref<AiSuggestion[]>;
}

const severityText: Record<RiskLevel, string> = {
  high: "高风险",
  medium: "中风险",
  low: "低风险",
};

export const useReviewReport = (state: ReviewReportState) => {
  const buildReviewReportMarkdown = () => {
    const data = state.currentAnalysis.value;
    const summary = data?.analysis.summary;
    const risks = data?.analysis.risks || [];
    const suggestions = data?.analysis.suggestions || [];
    const metrics = data?.analysis.metrics;
    const pr = data?.pr;

    const lines = [
      `# ${pr?.title || state.pullRequest.value.title}`,
      "",
      "## PR 信息",
      `- 仓库：${pr ? `${pr.owner}/${pr.repo}` : state.pullRequest.value.repository}`,
      `- PR：${pr?.url || state.analyzedUrl.value}`,
      `- 作者：${pr?.author || state.pullRequest.value.author}`,
      `- 分支：${pr?.headBranch || state.pullRequest.value.sourceBranch} -> ${pr?.baseBranch || state.pullRequest.value.targetBranch}`,
      `- 变更：${pr?.changedFiles ?? state.pullRequest.value.changedFiles} 个文件，+${pr?.additions ?? state.pullRequest.value.additions} / -${pr?.deletions ?? state.pullRequest.value.deletions}`,
      "",
      "## 总结",
      summary?.overview ?? state.pullRequest.value.description,
      "",
      "## 风险统计",
      `- 高风险：${metrics?.highRiskCount ?? state.riskStats.value.high}`,
      `- 中风险：${metrics?.mediumRiskCount ?? state.riskStats.value.medium}`,
      `- 低风险：${metrics?.lowRiskCount ?? state.riskStats.value.low}`,
      "",
      "## 变更模块",
      ...(summary?.changedModules?.length
        ? summary.changedModules.map((module) => `- ${module}`)
        : state.summaryItems.value.map((item) => `- ${item.text}`)),
      "",
      "## 风险问题",
      ...(risks.length
        ? risks.map((risk, index) => [
            `### ${index + 1}. ${risk.issue}`,
            `- 级别：${severityText[risk.severity]}`,
            `- 位置：${risk.file}${risk.line ? `:${risk.line}` : ""}`,
            `- 影响：${risk.impact}`,
            `- 建议：${risk.suggestion}`,
          ].join("\n"))
        : state.topIssues.value.map((issue, index) => `### ${index + 1}. ${issue.title}\n- 级别：${severityText[issue.level]}\n- 位置：${issue.file}`)),
      "",
      "## Review 建议",
      ...(suggestions.length
        ? suggestions.map((suggestion, index) => `${index + 1}. [${suggestion.type}] ${suggestion.file}：${suggestion.comment}`)
        : state.aiSuggestions.value.map((suggestion, index) => `${index + 1}. ${suggestion.title}：${suggestion.description}`)),
      "",
    ];

    return lines.join("\n");
  };

  const reportFileName = () => {
    const repo = (state.currentAnalysis.value?.pr.repo || state.pullRequest.value.repository || "review")
      .replace(/[^\w.-]+/g, "-");
    const number = state.currentAnalysis.value?.pr.number ? `-${state.currentAnalysis.value.pr.number}` : "";
    return `${repo}${number}-review-report.md`;
  };

  return {
    buildReviewReportMarkdown,
    reportFileName,
  };
};
