import type { DataAnalysis } from "@element-plus/icons-vue";

export type RiskLevel = "high" | "medium" | "low";

export interface NavItem {
  key: "analysis" | "history" | "reports" | "settings";
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
  high: number;
  medium: number;
  low: number;
}

export interface RiskStats {
  high: number;
  medium: number;
  low: number;
  total: number;
}

export interface AiSummaryStats {
  riskLevel: "低风险" | "中等风险" | "高风险";
  riskTone: "low" | "medium" | "high";
  riskIssues: number;
  involvedFiles: number;
  mergeAdvice: string;
}

export interface ChangedFile {
  path: string;
  folder: string;
  name: string;
  alerts: number;
  active?: boolean;
}

export interface CodeLine {
  line: number;
  mark: " " | "+" | "-";
  code: string;
}

export interface GitHubPRFile {
  filename: string;
  status: string;
  additions: number;
  deletions: number;
  changes: number;
  patch: string | null;
}

export interface GitHubPRResponse {
  owner: string;
  repo: string;
  number: number;
  title: string;
  body: string | null;
  state: string;
  author: string;
  html_url: string;
  base_branch: string;
  head_branch: string;
  changed_files: number;
  additions: number;
  deletions: number;
  files: GitHubPRFile[];
}

export interface AuthUser {
  id: number;
  email: string;
  created_at: string;
}

export interface AuthSession {
  user: AuthUser;
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface ReviewRecord {
  id: number;
  pr_url: string;
  pr_title: string | null;
  owner: string | null;
  repo: string | null;
  pr_number: number | null;
  status: string;
  file_count: number;
  risk_counts: Record<string, number> | null;
  duration_ms: number | null;
  created_at: string;
  completed_at: string | null;
}

export interface ReviewRecordDetail extends ReviewRecord {
  summary_json: Record<string, unknown> | null;
  result_json: ReviewAnalyzeResponse | null;
}

export interface ReviewRecordListResponse {
  items: ReviewRecord[];
  total: number;
  page: number;
  page_size: number;
}

export type FeedbackRating = "helpful" | "not_helpful" | "false_positive";

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
    changedFiles: number;
    additions: number;
    deletions: number;
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
