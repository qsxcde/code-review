import { apiRequest } from "./httpClient";
import type { ReviewStatsResponse } from "../types/reviewStats";

export const fetchReviewStats = (apiBaseUrl: string, accessToken: string) =>
  apiRequest<ReviewStatsResponse>(apiBaseUrl, "/review/stats", {
    accessToken,
  });
