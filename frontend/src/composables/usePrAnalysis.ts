import { computed, ref } from "vue";
import { ElMessage } from "element-plus";
import { analyzePR, fetchGitHubPR, isAsyncAnalyzeResponse, normalizeGitHubPrUrl, streamReviewProgress } from "../api/reviewApi";
import { fetchReviewRecordDetail } from "../api/historyApi";
import {
  defaultAiSummaryStats,
  defaultAiSuggestions,
  defaultChangedFiles,
  defaultCodeLines,
  defaultPullRequest,
  defaultRiskFiles,
  defaultRiskStats,
  defaultSummaryItems,
  defaultTopIssues,
} from "../data/reviewFixtures";
import {
  mapAnalyzeResponse,
  mapGitHubFiles,
  mapGitHubPRToPullRequest,
} from "../mappers/reviewMapper";
import { parsePatchToCodeLines } from "../utils/patchParser";
import type {
  PullRequestInfo,
  ReviewAnalyzeResponse,
  RiskLevel,
} from "../types/review";
import type { GitHubPRFile } from "../types/github";

export const riskLabel: Record<RiskLevel, string> = {
  high: "高风险",
  medium: "中风险",
  low: "低风险",
};

export const usePrAnalysis = (
  apiBaseUrl: string,
  getAccessToken: () => string,
  requireLogin: () => void,
  expireSession: () => void,
) => {
  const prUrl = ref("https://github.com/octocat/Hello-World/pull/6");
  const isAnalyzing = ref(false);
  const analysisStatus = ref<"idle" | "analyzing" | "completed" | "failed">("completed");
  const analysisDuration = ref(1.8);
  const analyzedUrl = ref(prUrl.value);
  const activeSummaryTag = ref("全部");
  const selectedRiskPath = ref("service/payment_service.py");
  const backendWarning = ref("");
  const errorMessage = ref("");
  const selectedCodePath = ref("service/payment_service.py");
  const prFiles = ref<GitHubPRFile[]>([]);
  const currentAnalysis = ref<ReviewAnalyzeResponse | null>(null);
  const pullRequest = ref<PullRequestInfo>({ ...defaultPullRequest });
  const summaryItems = ref([...defaultSummaryItems]);
  const riskFiles = ref([...defaultRiskFiles]);
  const riskStats = ref({ ...defaultRiskStats });
  const aiSummaryStats = ref({ ...defaultAiSummaryStats });
  const changedFiles = ref([...defaultChangedFiles]);
  const codeLines = ref([...defaultCodeLines]);
  const aiSuggestions = ref([...defaultAiSuggestions]);
  const topIssues = ref([...defaultTopIssues]);

  const summaryTags = computed(() => ["全部", ...Array.from(new Set(summaryItems.value.map((item) => item.tag)))]);
  const filteredSummaryItems = computed(() => {
    if (activeSummaryTag.value === "全部") return summaryItems.value;
    return summaryItems.value.filter((item) => item.tag === activeSummaryTag.value);
  });

  const selectedFileSuggestions = computed(() => {
    const matched = aiSuggestions.value.filter((suggestion) => suggestion.line === selectedCodePath.value);
    return matched.length > 0 ? matched : aiSuggestions.value;
  });

  const analysisStatusText = computed(() => {
    if (analysisStatus.value === "analyzing") return "正在获取 PR 变更并进行 AI 分析...";
    if (analysisStatus.value === "failed") return errorMessage.value || "分析失败，请稍后重试";
    return "分析完成";
  });

  const applyAnalyzeResult = (data: ReviewAnalyzeResponse, githubPR: { files: GitHubPRFile[] }) => {
    const mapped = mapAnalyzeResponse(data);

    currentAnalysis.value = data;
    prFiles.value = githubPR.files;
    pullRequest.value = {
      ...pullRequest.value,
      ...mapped.pullRequest,
    } as PullRequestInfo;
    summaryItems.value = mapped.summaryItems;
    riskFiles.value = mapped.riskFiles;
    riskStats.value = mapped.riskStats;
    aiSummaryStats.value = mapped.summaryStats;
    topIssues.value = mapped.topIssues;
    aiSuggestions.value = mapped.aiSuggestions;

    const firstRiskPath = mapped.riskFiles[0]?.path || "";
    const nextSelectedCodePath =
      githubPR.files.find((file) => file.filename === firstRiskPath)?.filename ||
      githubPR.files[0]?.filename ||
      firstRiskPath;

    selectedRiskPath.value = firstRiskPath;
    changedFiles.value = mapGitHubFiles(githubPR.files, mapped.riskFiles, nextSelectedCodePath);
    updateSelectedCodeFile(nextSelectedCodePath);

    activeSummaryTag.value = "全部";
    backendWarning.value = mapped.warnings;
    analysisDuration.value = data.durationMs / 1000;
    analysisStatus.value = "completed";
  };

  const updateSelectedCodeFile = (path: string) => {
    selectedCodePath.value = path;
    changedFiles.value = changedFiles.value.map((file) => ({
      ...file,
      active: file.path === path,
    }));

    const file = prFiles.value.find((item) => item.filename === path);
    const parsedLines = parsePatchToCodeLines(file?.patch);
    codeLines.value = parsedLines.length > 0
      ? parsedLines
      : [{ line: 1, mark: " ", code: file ? "该文件没有可展示的 patch 内容" : "暂无代码变更内容" }];
  };

  const handleAnalyze = async () => {
    const nextUrl = normalizeGitHubPrUrl(prUrl.value);

    if (!nextUrl) {
      errorMessage.value = "请输入正确的 GitHub Pull Request 链接";
      analysisStatus.value = "failed";
      ElMessage.warning(errorMessage.value);
      return;
    }

    const accessToken = getAccessToken();
    if (!accessToken) {
      requireLogin();
      ElMessage.warning("请先登录后再开始分析");
      return;
    }

    isAnalyzing.value = true;
    analysisStatus.value = "analyzing";
    errorMessage.value = "";
    analyzedUrl.value = nextUrl;
    prUrl.value = nextUrl;
    backendWarning.value = "";

    try {
      const [data, githubPR] = await Promise.all([
        analyzePR(nextUrl, apiBaseUrl, accessToken),
        fetchGitHubPR(nextUrl, apiBaseUrl, accessToken),
      ]);

      pullRequest.value = {
        ...pullRequest.value,
        ...mapGitHubPRToPullRequest(githubPR),
      } as PullRequestInfo;

      if (isAsyncAnalyzeResponse(data)) {
        backendWarning.value = `多 Agent 分析中，任务 #${data.record_id}`;
        await streamReviewProgress(apiBaseUrl, data.record_id, accessToken, (event) => {
          if (event.message) backendWarning.value = event.message;
          if (event.percent !== undefined) {
            backendWarning.value = `${backendWarning.value || "多 Agent 分析中"}（${event.percent}%）`;
          }
          if (event.event === "error") {
            throw new Error(event.message || "多 Agent 分析失败");
          }
        });

        const detail = await fetchReviewRecordDetail(apiBaseUrl, accessToken, data.record_id);
        if (!detail.result_json) {
          throw new Error("分析完成但未获取到结果");
        }
        applyAnalyzeResult(detail.result_json, githubPR);
      } else {
        applyAnalyzeResult(data, githubPR);
      }

      ElMessage.success("后端分析完成");
    } catch (error) {
      analysisStatus.value = "failed";
      const message = error instanceof Error ? error.message : "后端请求失败";
      errorMessage.value = `分析失败：${message}`;
      if (message.includes("401") || message.includes("Authentication") || message.includes("token")) {
        expireSession();
        requireLogin();
      }
      ElMessage.error(errorMessage.value);
    } finally {
      isAnalyzing.value = false;
    }
  };

  return {
    prUrl,
    isAnalyzing,
    analysisStatus,
    analysisDuration,
    analyzedUrl,
    activeSummaryTag,
    selectedRiskPath,
    backendWarning,
    errorMessage,
    selectedCodePath,
    currentAnalysis,
    pullRequest,
    summaryItems,
    riskFiles,
    riskStats,
    aiSummaryStats,
    changedFiles,
    codeLines,
    aiSuggestions,
    topIssues,
    summaryTags,
    filteredSummaryItems,
    selectedFileSuggestions,
    analysisStatusText,
    updateSelectedCodeFile,
    handleAnalyze,
  };
};
