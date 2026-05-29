import type { DataAnalysis } from "@element-plus/icons-vue";

export type RiskLevel = "high" | "medium" | "low";

export interface NavItem {
  label: string;
  icon: typeof DataAnalysis;
  active?: boolean;
}

export interface PullRequestInfo {
  repository: string;
  visibility: "公开仓库" | "私有仓库";
  title: string;
  description: string;
  author: string;
  sourceBranch: string;
  targetBranch: string;
  createdAt: string;
  updatedAt: string;
  state: "Open" | "Closed" | "Merged";
  changedFiles: number;
  additions: number;
  deletions: number;
}

export interface SummaryItem {
  text: string;
  tag: string;
  tone: "green" | "blue" | "orange" | "violet";
}

export interface RiskFile {
  path: string;
  count: number;
}

export interface ChangedFile {
  folder: string;
  name: string;
  alerts: number;
  active?: boolean;
}

export interface AiSuggestion {
  level: "高风险" | "中风险";
  title: string;
  line: string;
  description: string;
}

export interface InsightCard {
  title: string;
  icon: typeof DataAnalysis;
  rows: string[];
}

export interface Issue {
  title: string;
  file: string;
  level: RiskLevel;
}

export interface ReviewAnalyzeResponse {
  pr: {
    title: string;
    url: string;
    author: string;
    owner: string;
    repo: string;
    number: number;
    baseBranch: string;
    headBranch: string;
  };
  analysis: {
    summary: {
      overview: string;
      changedModules: string[];
      impact: string[];
    };
    risks: Array<{
      file: string;
      line: number | null;
      severity: RiskLevel;
      category: string;
      issue: string;
      impact: string;
      suggestion: string;
      confidence: number;
    }>;
    suggestions: Array<{
      file: string;
      type: "must_fix" | "should_fix" | "nice_to_have";
      comment: string;
    }>;
    metrics: {
      highRiskCount: number;
      mediumRiskCount: number;
      lowRiskCount: number;
      analyzedFileCount: number;
    };
    warnings: string[];
  };
  durationMs: number;
}
