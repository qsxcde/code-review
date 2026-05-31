export type { AuthSession, AuthUser } from "./auth";
export type { GitHubPRFile, GitHubPRResponse } from "./github";
export type { FeedbackRating, ReviewRecord, ReviewRecordDetail, ReviewRecordListResponse } from "./history";
export type { ActiveView, NavItem } from "./navigation";
export type { InsightCard } from "./ui";

export type RiskLevel = "high" | "medium" | "low";
export type AgentSource = "安全" | "性能" | "风格" | "通用";
export type AgentStatus = "idle" | "running" | "done" | "error" | "skipped";

export interface AgentStats {
  risks: number;
  high: number;
}

export interface ProgressState {
  percent: number;
  currentPhase: string;
  reconnecting: boolean;
  agents: Record<string, AgentStatus>;
  agentRisks: Record<string, AgentStats>;
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
  agentSource?: AgentSource;
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


export interface AiSuggestion {
  level: "高风险" | "中风险" | "低风险";
  title: string;
  line: string;
  description: string;
}

export interface Issue {
  title: string;
  file: string;
  level: RiskLevel;
  agentSource?: AgentSource;
  impact?: string;
  suggestion?: string;
  category?: string;
  confidence?: number;
}

export interface ReviewRisk {
  file: string;
  line: number | null;
  severity: RiskLevel;
  category: string;
  issue: string;
  impact: string;
  suggestion: string;
  confidence: number;
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
    risks: ReviewRisk[];
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
  analysis_mode?: "single" | "multi";
}

export interface ReviewAnalyzeTaskResponse {
  record_id: number;
  status: "running" | "pending";
}

export type ReviewAnalyzeResult = ReviewAnalyzeResponse | ReviewAnalyzeTaskResponse;

export interface ReviewProgressEvent {
  event: "phase_start" | "phase_done" | "agent_start" | "agent_done" | "agent_error" | "agent_skipped" | "complete" | "error";
  status?: "running" | "completed" | "failed";
  record_id?: number;
  review_record_id?: number;
  phase?: string;
  agent?: string;
  message?: string;
  percent?: number;
  risks?: number;
  high?: number;
}
