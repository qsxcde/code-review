import { apiRequest } from "./httpClient";
import type { GitHubPRResponse } from "../types/github";
import type { ReviewAnalyzeResult, ReviewProgressEvent } from "../types/review";

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
  apiRequest<ReviewAnalyzeResult>(apiBaseUrl, "/review/analyze", {
    method: "POST",
    accessToken,
    json: { prUrl },
  });

export const isAsyncAnalyzeResponse = (value: ReviewAnalyzeResult): value is Extract<ReviewAnalyzeResult, { record_id: number }> =>
  "record_id" in value && !("analysis" in value);

export const streamReviewProgress = async (
  apiBaseUrl: string,
  recordId: number,
  accessToken: string,
  onEvent: (event: ReviewProgressEvent) => void,
) => {
  const response = await fetch(`${apiBaseUrl}/review/analyze/${recordId}/stream`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!response.ok || !response.body) {
    throw new Error(`进度流连接失败：${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";

    for (const chunk of chunks) {
      const dataLine = chunk.split("\n").find((line) => line.startsWith("data: "));
      if (!dataLine) continue;

      const event = JSON.parse(dataLine.slice(6)) as ReviewProgressEvent;
      onEvent(event);
      if (event.event === "complete" || event.event === "error") {
        await reader.cancel();
        return;
      }
    }
  }
};
