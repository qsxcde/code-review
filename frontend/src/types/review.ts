export type Severity = "high" | "medium" | "low";
export type SuggestionType = "must_fix" | "should_fix" | "nice_to_have";

export interface ReviewAnalyzeRequest {
  prUrl: string;
}

export interface ReviewPRInfo {
  title: string;
  url: string;
  author: string;
  owner: string;
  repo: string;
  number: number;
  baseBranch: string;
  headBranch: string;
}

export interface ReviewSummary {
  overview: string;
  changedModules: string[];
  impact: string[];
}

export interface RiskItem {
  file: string;
  line: number | null;
  severity: Severity;
  category: string;
  issue: string;
  impact: string;
  suggestion: string;
  confidence: number;
}

export interface ReviewSuggestion {
  file: string;
  type: SuggestionType;
  comment: string;
}

export interface ReviewMetrics {
  highRiskCount: number;
  mediumRiskCount: number;
  lowRiskCount: number;
  analyzedFileCount: number;
}

export interface ReviewResult {
  summary: ReviewSummary;
  risks: RiskItem[];
  suggestions: ReviewSuggestion[];
  metrics: ReviewMetrics;
}

export interface ReviewAnalyzeResponse {
  pr: ReviewPRInfo;
  analysis: ReviewResult;
  durationMs: number;
}

