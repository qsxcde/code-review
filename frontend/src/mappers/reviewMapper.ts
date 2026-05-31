import type {
  AiSuggestion,
  AiSummaryStats,
  ChangedFile,
  Issue,
  PullRequestInfo,
  RiskFile,
  SummaryItem,
  ReviewAnalyzeResponse,
  AgentSource,
} from "../types/review";
import type { GitHubPRFile, GitHubPRResponse } from "../types/github";

export const toneForSummaryTag = (tag: string): SummaryItem["tone"] => {
  if (tag.includes("风险") || tag.includes("影响")) return "orange";
  if (tag.includes("模块")) return "blue";
  if (tag.includes("建议")) return "violet";
  return "green";
};

export const extractAgentSource = (issue: string): AgentSource => {
  if (issue.startsWith("[安全]")) return "安全";
  if (issue.startsWith("[性能]")) return "性能";
  if (issue.startsWith("[风格]")) return "风格";
  return "通用";
};

export const stripAgentPrefix = (value: string) =>
  value.replace(/^\[(安全|性能|风格)\]\s*/, "");

const toneForRiskSeverity = (severity: "high" | "medium" | "low"): SummaryItem["tone"] => {
  if (severity === "high") return "orange";
  if (severity === "medium") return "blue";
  return "green";
};

const GENERIC_AGENT_SOURCE: AgentSource = "通用";

const classifySummaryTag = (text: string, fallback = "优化"): string => {
  const value = text.toLowerCase();

  if (/(test|spec|测试|覆盖率|用例)/i.test(value)) return "测试";
  if (/(refactor|重构|模块|结构|状态流转)/i.test(value)) return "重构";
  if (/(add|新增|feature|引入|支持)/i.test(value)) return "新增功能";
  if (/(fix|修复|优化|建议|校验|异常|风险|impact|影响)/i.test(value)) return "优化";
  return fallback;
};

export const suggestionLevel = (type: "must_fix" | "should_fix" | "nice_to_have"): AiSuggestion["level"] =>
  type === "must_fix" ? "高风险" : "中风险";

const suggestionLevelForRisk = (severity: "high" | "medium" | "low"): AiSuggestion["level"] => {
  if (severity === "high") return "高风险";
  if (severity === "medium") return "中风险";
  return "低风险";
};

const riskPriority: Record<"high" | "medium" | "low", number> = {
  high: 0,
  medium: 1,
  low: 2,
};

export const mapAnalyzeResponse = (data: ReviewAnalyzeResponse) => {
  const risksByFile = data.analysis.risks.reduce<Record<string, RiskFile>>((acc, risk) => {
    const file = acc[risk.file] || {
      path: risk.file,
      count: 0,
      high: 0,
      medium: 0,
      low: 0,
    };

    file.count += 1;
    file[risk.severity] += 1;
    acc[risk.file] = file;
    return acc;
  }, {});

  const riskStats = {
    high: data.analysis.metrics.highRiskCount,
    medium: data.analysis.metrics.mediumRiskCount,
    low: data.analysis.metrics.lowRiskCount,
    total:
      data.analysis.metrics.highRiskCount +
      data.analysis.metrics.mediumRiskCount +
      data.analysis.metrics.lowRiskCount,
  };

  const riskTone: AiSummaryStats["riskTone"] =
    riskStats.high > 0 ? "high" : riskStats.medium > 0 ? "medium" : "low";

  const summaryStats: AiSummaryStats = {
    riskLevel: riskTone === "high" ? "高风险" : riskTone === "medium" ? "中等风险" : "低风险",
    riskTone,
    riskIssues: riskStats.total,
    involvedFiles: Object.keys(risksByFile).length || data.analysis.metrics.analyzedFileCount,
    mergeAdvice: riskStats.high > 0 ? "建议修复后合并" : riskStats.medium > 0 ? "建议确认后合并" : "可合并",
  };

  const pullRequest: Partial<PullRequestInfo> = {
    repository: `${data.pr.owner}/${data.pr.repo}`,
    title: data.pr.title,
    author: data.pr.author,
    sourceBranch: data.pr.headBranch,
    targetBranch: data.pr.baseBranch,
    changedFiles: data.pr.changedFiles,
    additions: data.pr.additions,
    deletions: data.pr.deletions,
  };

  const summaryItems: SummaryItem[] = [
    {
      text: data.analysis.summary.overview,
      tag: classifySummaryTag(data.analysis.summary.overview, "新增功能"),
      tone: toneForSummaryTag(classifySummaryTag(data.analysis.summary.overview, "新增功能")),
      agentSource: GENERIC_AGENT_SOURCE,
    },
    ...data.analysis.summary.changedModules.map((module) => {
      const tag = classifySummaryTag(module, "重构");
      return {
        text: `变更模块：${module}`,
        tag,
        tone: toneForSummaryTag(tag),
        agentSource: GENERIC_AGENT_SOURCE,
      };
    }),
    ...data.analysis.summary.impact.map((impact) => {
      const tag = classifySummaryTag(impact, "优化");
      return {
        text: impact,
        tag,
        tone: toneForSummaryTag(tag),
        agentSource: GENERIC_AGENT_SOURCE,
      };
    }),
    ...data.analysis.risks.slice(0, 4).map((risk) => ({
      text: `${risk.file}${risk.line ? `:${risk.line}` : ""} - ${stripAgentPrefix(risk.issue)}`,
      tag: extractAgentSource(risk.issue),
      tone: toneForRiskSeverity(risk.severity),
      agentSource: extractAgentSource(risk.issue),
    })),
    ...data.analysis.suggestions.slice(0, 3).map((suggestion) => {
      const tag = classifySummaryTag(suggestion.comment, suggestion.type === "nice_to_have" ? "测试" : "优化");
      return {
        text: suggestion.comment,
        tag,
        tone: toneForSummaryTag(tag),
        agentSource: extractAgentSource(suggestion.comment),
      };
    }),
  ];

  const riskFiles: RiskFile[] = Object.values(risksByFile)
    .sort((a, b) => b.high - a.high || b.count - a.count);

  const changedFiles: ChangedFile[] = Object.values(risksByFile)
    .sort((a, b) => b.count - a.count)
    .map((file, index) => {
      const parts = file.path.split("/");
      const name = parts.pop() || file.path;
      const folder = parts.join("/") || "root";

      return {
        path: file.path,
        folder,
        name,
        alerts: file.count,
        active: index === 0,
      };
    });

  const topIssues: Issue[] = [...data.analysis.risks]
    .sort((a, b) => riskPriority[a.severity] - riskPriority[b.severity])
    .map((risk) => ({
      title: stripAgentPrefix(risk.issue),
      file: `${risk.file}${risk.line ? `:${risk.line}` : ""}`,
      level: risk.severity,
      agentSource: extractAgentSource(risk.issue),
      impact: risk.impact,
      suggestion: risk.suggestion,
      category: risk.category,
      confidence: risk.confidence,
    }));

  const riskSuggestions: AiSuggestion[] = data.analysis.risks.map((risk) => ({
    level: suggestionLevelForRisk(risk.severity),
    title: stripAgentPrefix(risk.issue),
    line: risk.file,
    description: [
      risk.line ? `位置：${risk.file}:${risk.line}` : `位置：${risk.file}`,
      risk.impact ? `影响：${risk.impact}` : "",
      risk.suggestion ? `建议：${risk.suggestion}` : "",
    ].filter(Boolean).join("\n"),
  }));

  const reviewSuggestions: AiSuggestion[] = data.analysis.suggestions.map((suggestion) => ({
    level: suggestionLevel(suggestion.type),
    title: suggestion.type === "must_fix" ? "必须修复建议" : "Review 建议",
    line: suggestion.file,
    description: suggestion.comment,
  }));

  const aiSuggestions: AiSuggestion[] = [...riskSuggestions, ...reviewSuggestions];

  return {
    pullRequest,
    summaryItems,
    riskFiles,
    riskStats,
    summaryStats,
    changedFiles,
    topIssues,
    aiSuggestions,
    warnings: data.analysis.warnings.join("；"),
  };
};

export const mapGitHubFiles = (
  files: GitHubPRFile[],
  riskFiles: RiskFile[],
  selectedPath: string,
): ChangedFile[] => {
  const riskCountByPath = riskFiles.reduce<Record<string, number>>((acc, file) => {
    acc[file.path] = file.count;
    return acc;
  }, {});

  return files.map((file) => {
    const parts = file.filename.split("/");
    const name = parts.pop() || file.filename;
    const folder = parts.join("/") || "root";

    return {
      path: file.filename,
      folder,
      name,
      alerts: riskCountByPath[file.filename] || 0,
      active: file.filename === selectedPath,
    };
  });
};

const formatPrTime = (value: string | null) => {
  if (!value) return "";
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
};

export const mapGitHubPRToPullRequest = (data: GitHubPRResponse): Partial<PullRequestInfo> => ({
  repository: `${data.owner}/${data.repo}`,
  visibility: data.private ? "私有仓库" : "公开仓库",
  title: data.title,
  description: data.body || "暂无 PR 描述",
  author: data.author,
  sourceBranch: data.head_branch,
  targetBranch: data.base_branch,
  createdAt: formatPrTime(data.created_at),
  updatedAt: formatPrTime(data.updated_at),
  state: data.state === "closed" ? "Closed" : "Open",
  changedFiles: data.changed_files,
  additions: data.additions,
  deletions: data.deletions,
});
