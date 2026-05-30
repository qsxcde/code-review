import { apiRequest } from "./httpClient";
import type { GitHubPRResponse } from "../types/github";
import type { ReviewAnalyzeResponse } from "../types/review";

export const normalizeGitHubPrUrl = (value: string): string | null => {
  try {
    const parsed = new URL(value.trim());
    const parts = parsed.pathname.split("/").filter(Boolean);
    const [owner, repo, pull, number] = parts;

    if (parsed.hostname !== "github.com" || !owner || !repo || pull !== "pull" || !number || !/^\d+$/.test(number)) {
      return null;
    }

    return `https://github.com/${owner}/${repo}/pull/${number}`;
  } catch {
    return null;
  }
};

export const fetchGitHubPR = (prUrl: string, apiBaseUrl: string, accessToken: string) =>
  apiRequest<GitHubPRResponse>(apiBaseUrl, "/github/pr", {
    method: "POST",
    accessToken,
    json: { url: prUrl },
  });

export const analyzePR = (prUrl: string, apiBaseUrl: string, accessToken: string) =>
  apiRequest<ReviewAnalyzeResponse>(apiBaseUrl, "/review/analyze", {
    method: "POST",
    accessToken,
    json: { prUrl },
  });
