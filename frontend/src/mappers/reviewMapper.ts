import type {
  AiSuggestion,
  AiSummaryStats,
  ChangedFile,
  Issue,
  PullRequestInfo,
  RiskFile,
  SummaryItem,
  ReviewAnalyzeResponse,
} from "../types/review";
import type { GitHubPRFile, GitHubPRResponse } from "../types/github";

export const toneForSummaryTag = (tag: string): SummaryItem["tone"] => {
  if (tag.includes("风险") || tag.includes("影响")) return "orange";
  if (tag.includes("模块")) return "blue";
  if (tag.includes("建议")) return "violet";
  return "green";
};

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
    description: data.analysis.summary.overview,
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
    },
    ...data.analysis.summary.changedModules.map((module) => {
      const tag = classifySummaryTag(module, "重构");
      return {
        text: `变更模块：${module}`,
        tag,
        tone: toneForSummaryTag(tag),
      };
    }),
    ...data.analysis.summary.impact.map((impact) => {
      const tag = classifySummaryTag(impact, "优化");
      return {
        text: impact,
        tag,
        tone: toneForSummaryTag(tag),
      };
    }),
    ...data.analysis.risks.slice(0, 4).map((risk) => ({
      text: `${risk.file}${risk.line ? `:${risk.line}` : ""} - ${risk.issue}`,
      tag: "优化",
      tone: toneForSummaryTag("优化"),
    })),
    ...data.analysis.suggestions.slice(0, 3).map((suggestion) => {
      const tag = classifySummaryTag(suggestion.comment, suggestion.type === "nice_to_have" ? "测试" : "优化");
      return {
        text: suggestion.comment,
        tag,
        tone: toneForSummaryTag(tag),
      };
    }),
  ];

  const riskFiles: RiskFile[] = Object.values(risksByFile)
    .sort((a, b) => b.high - a.high || b.count - a.count)
    .slice(0, 3);

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

  const topIssues: Issue[] = data.analysis.risks.slice(0, 3).map((risk) => ({
    title: risk.issue,
    file: `${risk.file}${risk.line ? `:${risk.line}` : ""}`,
    level: risk.severity,
  }));

  const aiSuggestions: AiSuggestion[] = data.analysis.suggestions.slice(0, 3).map((suggestion) => ({
    level: suggestionLevel(suggestion.type),
    title: suggestion.type === "must_fix" ? "必须修复建议" : "Review 建议",
    line: suggestion.file,
    description: suggestion.comment,
  }));

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

export const mapGitHubPRToPullRequest = (data: GitHubPRResponse): Partial<PullRequestInfo> => ({
  repository: `${data.owner}/${data.repo}`,
  title: data.title,
  description: data.body || "暂无 PR 描述",
  author: data.author,
  sourceBranch: data.head_branch,
  targetBranch: data.base_branch,
  state: data.state === "closed" ? "Closed" : "Open",
  changedFiles: data.changed_files,
  additions: data.additions,
  deletions: data.deletions,
});
