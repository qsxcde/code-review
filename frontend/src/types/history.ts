import type { ReviewAnalyzeResponse } from "./review";

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
