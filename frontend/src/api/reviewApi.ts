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

  return parseReviewAnalyzeResponse(await response.json());
}

function parseReviewAnalyzeResponse(data: unknown): ReviewAnalyzeResponse {
  if (!isRecord(data)) {
    throw new Error("后端响应格式不正确");
  }

  const pr = data.pr;
  const analysis = data.analysis;
  if (!isRecord(pr) || !isRecord(analysis)) {
    throw new Error("后端响应缺少 PR 或分析结果");
  }

  assertString(pr.title, "pr.title");
  assertString(pr.url, "pr.url");
  assertString(pr.author, "pr.author");
  assertString(pr.owner, "pr.owner");
  assertString(pr.repo, "pr.repo");
  assertNumber(pr.number, "pr.number");
  assertString(pr.baseBranch, "pr.baseBranch");
  assertString(pr.headBranch, "pr.headBranch");

  const summary = analysis.summary;
  const metrics = analysis.metrics;
  if (!isRecord(summary) || !isRecord(metrics)) {
    throw new Error("后端响应缺少 summary 或 metrics");
  }

  assertString(summary.overview, "analysis.summary.overview");
  assertStringArray(summary.changedModules, "analysis.summary.changedModules");
  assertStringArray(summary.impact, "analysis.summary.impact");
  assertRiskArray(analysis.risks);
  assertSuggestionArray(analysis.suggestions);
  assertStringArray(analysis.warnings, "analysis.warnings");
  assertNumber(metrics.highRiskCount, "analysis.metrics.highRiskCount");
  assertNumber(metrics.mediumRiskCount, "analysis.metrics.mediumRiskCount");
  assertNumber(metrics.lowRiskCount, "analysis.metrics.lowRiskCount");
  assertNumber(metrics.analyzedFileCount, "analysis.metrics.analyzedFileCount");
  assertNumber(data.durationMs, "durationMs");

  return data as unknown as ReviewAnalyzeResponse;
}

function assertRiskArray(value: unknown): void {
  if (!Array.isArray(value)) {
    throw new Error("后端响应字段 analysis.risks 格式不正确");
  }

  for (const risk of value) {
    if (!isRecord(risk)) {
      throw new Error("后端响应字段 analysis.risks 格式不正确");
    }
    assertString(risk.file, "risk.file");
    if (risk.line !== null) {
      assertNumber(risk.line, "risk.line");
    }
    assertOneOf(risk.severity, ["high", "medium", "low"], "risk.severity");
    assertString(risk.category, "risk.category");
    assertString(risk.issue, "risk.issue");
    assertString(risk.impact, "risk.impact");
    assertString(risk.suggestion, "risk.suggestion");
    assertNumber(risk.confidence, "risk.confidence");
  }
}

function assertSuggestionArray(value: unknown): void {
  if (!Array.isArray(value)) {
    throw new Error("后端响应字段 analysis.suggestions 格式不正确");
  }

  for (const suggestion of value) {
    if (!isRecord(suggestion)) {
      throw new Error("后端响应字段 analysis.suggestions 格式不正确");
    }
    assertString(suggestion.file, "suggestion.file");
    assertOneOf(
      suggestion.type,
      ["must_fix", "should_fix", "nice_to_have"],
      "suggestion.type",
    );
    assertString(suggestion.comment, "suggestion.comment");
  }
}

function assertStringArray(value: unknown, field: string): void {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string")) {
    throw new Error(`后端响应字段 ${field} 格式不正确`);
  }
}

function assertString(value: unknown, field: string): void {
  if (typeof value !== "string") {
    throw new Error(`后端响应字段 ${field} 格式不正确`);
  }
}

function assertNumber(value: unknown, field: string): void {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`后端响应字段 ${field} 格式不正确`);
  }
}

function assertOneOf(value: unknown, allowed: string[], field: string): void {
  if (typeof value !== "string" || !allowed.includes(value)) {
    throw new Error(`后端响应字段 ${field} 格式不正确`);
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
