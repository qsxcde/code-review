import type { ReviewAnalyzeResponse, SummaryItem, AiSuggestion, RiskFile, Issue, PullRequestInfo } from "../types/review";

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

export const suggestionLevel = (type: "must_fix" | "should_fix" | "nice_to_have"): AiSuggestion["level"] =>
  type === "must_fix" ? "高风险" : "中风险";

export const mapAnalyzeResponse = (data: ReviewAnalyzeResponse) => {
  const risksByFile = data.analysis.risks.reduce<Record<string, number>>((acc, risk) => {
    acc[risk.file] = (acc[risk.file] || 0) + 1;
    return acc;
  }, {});

  const pullRequest: Partial<PullRequestInfo> & { changedFiles: number } = {
    repository: `${data.pr.owner}/${data.pr.repo}`,
    title: data.pr.title,
    description: data.analysis.summary.overview,
    author: data.pr.author,
    sourceBranch: data.pr.headBranch,
    targetBranch: data.pr.baseBranch,
    changedFiles: data.analysis.metrics.analyzedFileCount,
  };

  const summaryItems: SummaryItem[] = [
    { text: data.analysis.summary.overview, tag: "总览", tone: "green" },
    ...data.analysis.summary.changedModules.map((module) => ({
      text: `变更模块：${module}`,
      tag: "模块",
      tone: toneForSummaryTag("模块"),
    })),
    ...data.analysis.summary.impact.map((impact) => ({
      text: impact,
      tag: "影响",
      tone: toneForSummaryTag("影响"),
    })),
  ];

  const riskFiles: RiskFile[] = Object.entries(risksByFile)
    .map(([path, count]) => ({ path, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5);

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
