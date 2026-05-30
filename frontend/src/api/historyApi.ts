import { apiRequest } from "./httpClient";
import type { FeedbackRating, ReviewRecordDetail, ReviewRecordListResponse } from "../types/history";

export interface HistoryQuery {
  page: number;
  pageSize: number;
  status?: string;
  owner?: string;
  repo?: string;
}

export const fetchReviewRecords = async (
  apiBaseUrl: string,
  accessToken: string,
  query: HistoryQuery,
) => {
  const params = new URLSearchParams({
    page: String(query.page),
    page_size: String(query.pageSize),
  });

  if (query.status) params.set("status", query.status);
  if (query.owner) params.set("owner", query.owner);
  if (query.repo) params.set("repo", query.repo);

  return apiRequest<ReviewRecordListResponse>(apiBaseUrl, `/review/records?${params.toString()}`, {
    accessToken,
  });
};

export const fetchReviewRecordDetail = async (
  apiBaseUrl: string,
  accessToken: string,
  recordId: number,
) => {
  return apiRequest<ReviewRecordDetail>(apiBaseUrl, `/review/records/${recordId}`, {
    accessToken,
  });
};

export const deleteReviewRecord = async (
  apiBaseUrl: string,
  accessToken: string,
  recordId: number,
) => {
  await apiRequest<void>(apiBaseUrl, `/review/records/${recordId}`, {
    method: "DELETE",
    accessToken,
  });
};

export const submitReviewFeedback = async (
  apiBaseUrl: string,
  accessToken: string,
  recordId: number,
  riskIndex: number,
  rating: FeedbackRating,
) => {
  return apiRequest<unknown>(apiBaseUrl, `/review/records/${recordId}/feedback`, {
    method: "POST",
    accessToken,
    json: { risk_index: riskIndex, rating },
  });
};
