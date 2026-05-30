import type {
  ReviewAnalyzeResponse,
  SummaryItem,
  AiSuggestion,
  RiskFile,
  Issue,
  PullRequestInfo,
  ChangedFile,
  AiSummaryStats,
} from "../types/review";

export const normalizeGitHubPrUrl = (value: string): string | null => {
  try {
    const parsed = new URL(value.trim());
    const parts = parsed.pathname.split("/").filter(Boolean);
    const [owner, repo, pull, number] = parts;

    if (parsed.hostname !== "github.com" || !owner || !repo || pull !== "pull" || !number || !/^\d+$/.test(number)) {
      return null;
    }

    return `https://github.com/${owner}/${repo}/pull/${number}`;
  } catch {
    return null;
  }
};

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

export const analyzePR = async (prUrl: string, apiBaseUrl: string, reviewApiToken: string) => {
  const response = await fetch(`${apiBaseUrl}/review/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(reviewApiToken ? { Authorization: `Bearer ${reviewApiToken}` } : {}),
    },
    body: JSON.stringify({ prUrl }),
  });

  if (!response.ok) {
    let detail = `后端返回 ${response.status}`;
    try {
      const errorBody = (await response.json()) as { detail?: unknown };
      if (typeof errorBody.detail === "string") {
        detail = errorBody.detail;
      } else if (errorBody.detail && typeof errorBody.detail === "object" && "message" in errorBody.detail) {
        detail = String((errorBody.detail as { message: unknown }).message);
      }
    } catch {
      // Keep the status-only message when the response body is not JSON.
    }
    throw new Error(detail);
  }

  return (await response.json()) as ReviewAnalyzeResponse;
};
