import { apiRequest } from "./httpClient";
import type {
  ReviewRule,
  ReviewRuleCategory,
  ReviewRuleListResponse,
  ReviewRulePayload,
  ReviewRuleUpdatePayload,
} from "../types/reviewRule";

const rulesPath = "/review/rules";

export const fetchReviewRules = (
  apiBaseUrl: string,
  accessToken: string,
  category?: ReviewRuleCategory | "",
) => {
  const query = category ? `?category=${encodeURIComponent(category)}` : "";
  return apiRequest<ReviewRuleListResponse>(apiBaseUrl, `${rulesPath}${query}`, {
    accessToken,
  });
};

export const createReviewRule = (
  apiBaseUrl: string,
  accessToken: string,
  payload: ReviewRulePayload,
) =>
  apiRequest<ReviewRule>(apiBaseUrl, rulesPath, {
    method: "POST",
    accessToken,
    json: payload,
  });

export const updateReviewRule = (
  apiBaseUrl: string,
  accessToken: string,
  ruleId: number,
  payload: ReviewRuleUpdatePayload,
) =>
  apiRequest<ReviewRule>(apiBaseUrl, `${rulesPath}/${ruleId}`, {
    method: "PUT",
    accessToken,
    json: payload,
  });

export const deleteReviewRule = (
  apiBaseUrl: string,
  accessToken: string,
  ruleId: number,
) =>
  apiRequest<void>(apiBaseUrl, `${rulesPath}/${ruleId}`, {
    method: "DELETE",
    accessToken,
  });
