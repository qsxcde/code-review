import type {
  AiSuggestion,
  Issue,
  PullRequestInfo,
  ReviewAnalyzeResponse,
  RiskLevel,
  RiskStats,
  SummaryItem,
} from "../types/review";

const severityText: Record<RiskLevel, string> = {
  high: "高风险",
  medium: "中风险",
  low: "低风险",
};

export interface ReviewReportInput {
  currentAnalysis: ReviewAnalyzeResponse | null;
  pullRequest: PullRequestInfo;
  analyzedUrl: string;
  riskStats: RiskStats;
  summaryItems: SummaryItem[];
  topIssues: Issue[];
  aiSuggestions: AiSuggestion[];
}

export const buildReviewReportMarkdown = (input: ReviewReportInput): string => {
  const data = input.currentAnalysis;
  const summary = data?.analysis.summary;
  const risks = data?.analysis.risks || [];
  const suggestions = data?.analysis.suggestions || [];
  const metrics = data?.analysis.metrics;
  const pr = data?.pr;

  const lines = [
    `# ${pr?.title || input.pullRequest.title}`,
    "",
    "## PR 信息",
    `- 仓库：${pr ? `${pr.owner}/${pr.repo}` : input.pullRequest.repository}`,
    `- PR：${pr?.url || input.analyzedUrl}`,
    `- 作者：${pr?.author || input.pullRequest.author}`,
    `- 分支：${pr?.headBranch || input.pullRequest.sourceBranch} -> ${pr?.baseBranch || input.pullRequest.targetBranch}`,
    `- 变更：${pr?.changedFiles ?? input.pullRequest.changedFiles} 个文件，+${pr?.additions ?? input.pullRequest.additions} / -${pr?.deletions ?? input.pullRequest.deletions}`,
    "",
    "## 总结",
    summary?.overview ?? input.pullRequest.description,
    "",
    "## 风险统计",
    `- 高风险：${metrics?.highRiskCount ?? input.riskStats.high}`,
    `- 中风险：${metrics?.mediumRiskCount ?? input.riskStats.medium}`,
    `- 低风险：${metrics?.lowRiskCount ?? input.riskStats.low}`,
    "",
    "## 变更模块",
    ...(summary?.changedModules?.length
      ? summary.changedModules.map((module) => `- ${module}`)
      : input.summaryItems.map((item) => `- ${item.text}`)),
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
      : input.topIssues.map((issue, index) => `### ${index + 1}. ${issue.title}\n- 级别：${severityText[issue.level]}\n- 位置：${issue.file}`)),
    "",
    "## Review 建议",
    ...(suggestions.length
      ? suggestions.map((suggestion, index) => `${index + 1}. [${suggestion.type}] ${suggestion.file}：${suggestion.comment}`)
      : input.aiSuggestions.map((suggestion, index) => `${index + 1}. ${suggestion.title}：${suggestion.description}`)),
    "",
  ];

  return lines.join("\n");
};

export const reviewReportFileName = (input: ReviewReportInput): string => {
  const repo = (input.currentAnalysis?.pr.repo || input.pullRequest.repository || "review")
    .replace(/[^\w.-]+/g, "-");
  const number = input.currentAnalysis?.pr.number ? `-${input.currentAnalysis.pr.number}` : "";
  return `${repo}${number}-review-report.md`;
};
