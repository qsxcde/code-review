import type { ReviewAnalyzeResponse } from "../types/review";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
const REVIEW_API_TOKEN = import.meta.env.VITE_REVIEW_API_TOKEN;
const DEFAULT_TIMEOUT_MS = 120000;

interface ApiErrorBody {
  detail?: unknown;
}

interface ApiErrorDetail {
  message?: unknown;
}

interface AnalyzeOptions {
  signal?: AbortSignal;
  timeoutMs?: number;
}

export async function analyzePullRequest(
  prUrl: string,
  options: AnalyzeOptions = {},
): Promise<ReviewAnalyzeResponse> {
  if (!REVIEW_API_TOKEN) {
    throw new Error("VITE_REVIEW_API_TOKEN 未配置");
  }

  const controller = new AbortController();
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  let timeoutId: ReturnType<typeof window.setTimeout> | undefined;
  let timedOut = false;

  const abortRequest = () => {
    if (!controller.signal.aborted) {
      controller.abort();
    }
  };

  if (options.signal?.aborted) {
    abortRequest();
  } else {
    options.signal?.addEventListener("abort", abortRequest, { once: true });
  }

  if (timeoutMs > 0) {
    timeoutId = window.setTimeout(() => {
      timedOut = true;
      abortRequest();
    }, timeoutMs);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/review/analyze`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${REVIEW_API_TOKEN}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ prUrl }),
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(timedOut ? "请求超时，请稍后重试" : "请求已取消");
    }
    throw error;
  } finally {
    if (timeoutId) {
      window.clearTimeout(timeoutId);
    }
    options.signal?.removeEventListener("abort", abortRequest);
  }

  if (!response.ok) {
    let message = `请求失败：${response.status}`;
    try {
      const body = (await response.json()) as ApiErrorBody;
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (Array.isArray(body.detail)) {
        message = "请求参数格式不正确";
      } else if (body.detail && typeof body.detail === "object") {
        const detail = body.detail as ApiErrorDetail;
        if (typeof detail.message === "string") {
          message = detail.message;
        }
      }
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }

  return (await response.json()) as ReviewAnalyzeResponse;
}
