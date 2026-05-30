import type { FeedbackRating, ReviewRecordDetail, ReviewRecordListResponse } from "../types/review";

const readErrorMessage = async (response: Response) => {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // Keep status-only fallback.
  }

  return `请求失败：${response.status}`;
};

const authHeaders = (accessToken: string) => ({
  "Content-Type": "application/json",
  Authorization: `Bearer ${accessToken}`,
});

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

  const response = await fetch(`${apiBaseUrl}/review/records?${params.toString()}`, {
    headers: authHeaders(accessToken),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return (await response.json()) as ReviewRecordListResponse;
};

export const fetchReviewRecordDetail = async (
  apiBaseUrl: string,
  accessToken: string,
  recordId: number,
) => {
  const response = await fetch(`${apiBaseUrl}/review/records/${recordId}`, {
    headers: authHeaders(accessToken),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return (await response.json()) as ReviewRecordDetail;
};

export const deleteReviewRecord = async (
  apiBaseUrl: string,
  accessToken: string,
  recordId: number,
) => {
  const response = await fetch(`${apiBaseUrl}/review/records/${recordId}`, {
    method: "DELETE",
    headers: authHeaders(accessToken),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }
};

export const submitReviewFeedback = async (
  apiBaseUrl: string,
  accessToken: string,
  recordId: number,
  riskIndex: number,
  rating: FeedbackRating,
) => {
  const response = await fetch(`${apiBaseUrl}/review/records/${recordId}/feedback`, {
    method: "POST",
    headers: authHeaders(accessToken),
    body: JSON.stringify({ risk_index: riskIndex, rating }),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
};
