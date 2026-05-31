export interface AgentFeedbackStats {
  agent: string;
  total_risks: number;
  helpful: number;
  not_helpful: number;
  false_positive: number;
  false_positive_rate: number;
}

export interface RecentFalsePositive {
  record_id: number;
  file: string;
  issue: string;
  created_at: string;
}

export interface ReviewStatsResponse {
  total_analyses: number;
  total_risks_flagged: number;
  feedback_coverage: number;
  by_agent: AgentFeedbackStats[];
  false_positive_rate: number;
  recent_false_positives: RecentFalsePositive[];
}
