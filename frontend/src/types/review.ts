export type Severity = "high" | "medium" | "low";
export type SuggestionType = "must_fix" | "should_fix" | "nice_to_have";

export type PullRequestInfo = {
  title: string;
  url: string;
  author: string;
  baseBranch?: string;
  headBranch?: string;
};

export type ReviewSummary = {
  overview: string;
  changedModules: string[];
  impact: string[];
};

export type RiskItem = {
  file: string;
  line?: number;
  severity: Severity;
  category: string;
  issue: string;
  impact: string;
  suggestion: string;
  confidence: number;
};

export type ReviewSuggestion = {
  file: string;
  type: SuggestionType;
  comment: string;
};

export type ReviewMetrics = {
  highRiskCount: number;
  mediumRiskCount: number;
  lowRiskCount: number;
  analyzedFileCount: number;
};

export type ReviewResult = {
  summary: ReviewSummary;
  risks: RiskItem[];
  suggestions: ReviewSuggestion[];
  metrics: ReviewMetrics;
};

export type AnalyzeResponse = {
  pr: PullRequestInfo;
  analysis: ReviewResult;
  durationMs: number;
};
