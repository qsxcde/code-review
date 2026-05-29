import type { AnalyzeResponse } from "../types/review";

const demoResult: AnalyzeResponse = {
  pr: {
    title: "Add login captcha verification",
    url: "https://github.com/example/project/pull/123",
    author: "developer",
    baseBranch: "main",
    headBranch: "feature/captcha"
  },
  analysis: {
    summary: {
      overview:
        "本 PR 为登录流程新增验证码校验，并调整认证服务的异常处理逻辑。整体变更集中在 auth 模块，对登录成功率、安全校验和失败路径有直接影响。",
      changedModules: ["auth", "login api", "unit tests"],
      impact: ["登录接口", "认证服务", "验证码失败分支", "登录相关测试"]
    },
    risks: [
      {
        file: "src/auth/login.ts",
        line: 42,
        severity: "high",
        category: "security",
        issue: "验证码校验失败后仍可能继续执行登录逻辑。",
        impact: "攻击者可能绕过验证码限制，导致登录防护失效。",
        suggestion: "建议在验证码校验失败时立即 return，或抛出明确的业务异常。",
        confidence: 0.86
      },
      {
        file: "src/auth/AuthService.ts",
        line: 88,
        severity: "medium",
        category: "exception",
        issue: "外部验证码服务异常时缺少降级处理。",
        impact: "第三方服务短暂不可用时，登录接口可能返回不稳定错误。",
        suggestion: "建议补充超时、重试或明确的失败响应，避免异常直接透出。",
        confidence: 0.72
      },
      {
        file: "tests/auth/login.test.ts",
        severity: "low",
        category: "test",
        issue: "当前测试覆盖了验证码成功路径，但缺少失败路径断言。",
        impact: "后续改动可能破坏安全校验而不被测试发现。",
        suggestion: "建议增加验证码错误、过期和服务异常场景的测试用例。",
        confidence: 0.68
      }
    ],
    suggestions: [
      {
        file: "src/auth/login.ts",
        type: "must_fix",
        comment: "验证码校验失败时应立即中断登录流程。"
      },
      {
        file: "tests/auth/login.test.ts",
        type: "should_fix",
        comment: "补充验证码失败路径和异常路径的单元测试。"
      },
      {
        file: "src/auth/AuthService.ts",
        type: "nice_to_have",
        comment: "可以把验证码校验结果封装为显式类型，减少布尔值误用。"
      }
    ],
    metrics: {
      highRiskCount: 1,
      mediumRiskCount: 1,
      lowRiskCount: 1,
      analyzedFileCount: 3
    }
  },
  durationMs: 8600
};

export async function analyzePullRequest(prUrl: string): Promise<AnalyzeResponse> {
  const normalizedUrl = prUrl.trim();

  if (!normalizedUrl) {
    return demoResult;
  }

  try {
    const response = await fetch("/api/review/analyze", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ prUrl: normalizedUrl })
    });

    if (!response.ok) {
      throw new Error(`分析请求失败：${response.status}`);
    }

    return (await response.json()) as AnalyzeResponse;
  } catch (error) {
    console.warn("Using demo review result because backend is unavailable.", error);
    return {
      ...demoResult,
      pr: {
        ...demoResult.pr,
        url: normalizedUrl || demoResult.pr.url
      }
    };
  }
}
