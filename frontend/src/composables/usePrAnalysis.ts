import { computed, ref } from "vue";
import { ElMessage } from "element-plus";
import { analyzePR, fetchGitHubPR, isAsyncAnalyzeResponse, normalizeGitHubPrUrl, streamReviewProgress } from "../api/reviewApi";
import { fetchReviewRecordDetail } from "../api/historyApi";
import { useAnalysisProgress } from "./useAnalysisProgress";
import { useReviewFeedback } from "./useReviewFeedback";
import {
  mapAnalyzeResponse,
  mapGitHubFiles,
  mapGitHubPRToPullRequest,
} from "../mappers/reviewMapper";
import { extractAgentSource } from "../mappers/reviewMapper";
import { parsePatchToCodeLines } from "../utils/patchParser";
import type {
  AgentStats,
  AgentSource,
  AiSuggestion,
  AiSummaryStats,
  ChangedFile,
  CodeLine,
  Issue,
  PullRequestInfo,
  ReviewAnalyzeResponse,
  RiskFile,
  RiskStats,
  SummaryItem,
} from "../types/review";
import type { GitHubPRFile } from "../types/github";

export { riskLabel } from "../constants/labels";

export const usePrAnalysis = (
  apiBaseUrl: string,
  getAccessToken: () => string,
  requireLogin: () => void,
  expireSession: () => void,
) => {
  const prUrl = ref("https://github.com/octocat/Hello-World/pull/6");
  const isAnalyzing = ref(false);
  const analysisStatus = ref<"idle" | "analyzing" | "completed" | "failed">("idle");
  const analysisDuration = ref(1.8);
  const analyzedUrl = ref(prUrl.value);
  const activeSummaryTag = ref("全部");
  const selectedRiskPath = ref("service/payment_service.py");
  const backendWarning = ref("");
  const errorMessage = ref("");
  const selectedCodePath = ref("service/payment_service.py");
  const prFiles = ref<GitHubPRFile[]>([]);
  const emptyPullRequest: PullRequestInfo = {
    repository: "",
    visibility: "公开仓库",
    title: "",
    description: "",
    author: "",
    sourceBranch: "",
    targetBranch: "",
    createdAt: "",
    updatedAt: "",
    state: "Open",
    changedFiles: 0,
    additions: 0,
    deletions: 0,
  };

  const currentAnalysis = ref<ReviewAnalyzeResponse | null>(null);
  const pullRequest = ref<PullRequestInfo>({ ...emptyPullRequest });
  const summaryItems = ref<SummaryItem[]>([]);
  const riskFiles = ref<RiskFile[]>([]);
  const riskStats = ref<RiskStats>({ high: 0, medium: 0, low: 0, total: 0 });
  const aiSummaryStats = ref<AiSummaryStats>({ riskLevel: "低风险", riskTone: "low", riskIssues: 0, involvedFiles: 0, mergeAdvice: "" });
  const changedFiles = ref<ChangedFile[]>([]);
  const codeLines = ref<CodeLine[]>([]);
  const aiSuggestions = ref<AiSuggestion[]>([]);
  const topIssues = ref<Issue[]>([]);
  const currentRecordId = ref<number | null>(null);
  const feedback = useReviewFeedback(apiBaseUrl, getAccessToken);
  const progress = useAnalysisProgress();

  const summaryTagToSource: Record<string, AgentSource | "all"> = {
    "全部": "all",
    "安全": "安全",
    "性能": "性能",
    "风格总结": "风格",
    "通用总结": "通用",
  };

  const summaryTags = computed(() =>
    analysisMode.value === "multi" ? ["全部", "安全", "性能", "风格总结"] : ["通用总结"],
  );

  const filteredSummaryItems = computed(() => {
    const source = summaryTagToSource[activeSummaryTag.value] || "all";
    if (source === "all") return summaryItems.value;
    return summaryItems.value.filter((item) => item.agentSource === source);
  });

  const selectedFileSuggestions = computed(() => {
    return aiSuggestions.value.filter((suggestion) => suggestion.line === selectedCodePath.value);
  });

  const analysisStatusText = computed(() => {
    if (analysisStatus.value === "idle") return "提交 PR 链接开始 AI 代码审查";
    if (analysisStatus.value === "analyzing") return "正在获取 PR 变更并进行 AI 分析...";
    if (analysisStatus.value === "failed") return errorMessage.value || "分析失败，请稍后重试";
    return "分析完成";
  });

  const analysisMode = computed(() => currentAnalysis.value?.analysis_mode || (currentRecordId.value ? "multi" : "single"));
  const showAsyncProgress = computed(() => isAnalyzing.value && currentRecordId.value !== null);

  const agentStats = computed<Record<string, AgentStats>>(() => {
    const stats: Record<string, AgentStats> = {
      "安全": { risks: 0, high: 0 },
      "性能": { risks: 0, high: 0 },
      "风格": { risks: 0, high: 0 },
      "通用": { risks: 0, high: 0 },
    };

    for (const risk of currentAnalysis.value?.analysis.risks || []) {
      const source = extractAgentSource(risk.issue);
      stats[source].risks += 1;
      if (risk.severity === "high") stats[source].high += 1;
    }

    return stats;
  });

  const languages = computed(() => {
    const values = prFiles.value
      .map((file) => file.filename.split(".").pop()?.toLowerCase())
      .filter((value): value is string => Boolean(value));
    return Array.from(new Set(values));
  });

  const applyAnalyzeResult = (data: ReviewAnalyzeResponse, githubPR: { files: GitHubPRFile[] }, recordId?: number | null) => {
    const mapped = mapAnalyzeResponse(data);

    currentAnalysis.value = data;
    currentRecordId.value = recordId ?? null;
    feedback.setRecordId(currentRecordId.value);
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

    activeSummaryTag.value = (data.analysis_mode || analysisMode.value) === "multi" ? "全部" : "通用总结";
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
      : [{ line: 1, mark: " ", code: file ? "该文件无可展示的代码差异（可能为二进制或重命名）" : "选择左侧文件查看代码变更" }];
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
    currentRecordId.value = null;
    feedback.setRecordId(null);
    progress.resetProgress();

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
        currentRecordId.value = data.record_id;
        progress.progressState.currentPhase = `多 Agent 分析中，任务 #${data.record_id}`;
        let streamError = "";
        await streamReviewProgress(apiBaseUrl, data.record_id, accessToken, (event) => {
          progress.updateProgress(event);
          if (event.event === "error") {
            streamError = event.message || "多 Agent 分析失败";
          }
        });
        if (streamError) throw new Error(streamError);

        const detail = await fetchReviewRecordDetail(apiBaseUrl, accessToken, data.record_id);
        if (!detail.result_json) {
          throw new Error("分析完成但未获取到结果");
        }
        applyAnalyzeResult(detail.result_json, githubPR, data.record_id);
      } else {
        applyAnalyzeResult({ ...data, analysis_mode: data.analysis_mode || "single" }, githubPR, null);
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
    currentRecordId,
    feedbackState: feedback.feedbackState,
    progressState: progress.progressState,
    agentStats,
    analysisMode,
    showAsyncProgress,
    languages,
    summaryTags,
    filteredSummaryItems,
    selectedFileSuggestions,
    analysisStatusText,
    updateSelectedCodeFile,
    sendAnalysisFeedback: feedback.sendFeedback,
    handleAnalyze,
  };
};
