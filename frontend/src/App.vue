<script setup lang="ts">
import { computed, ref } from "vue";
import { ElMessage } from "element-plus";
import {
  Clock,
  DataAnalysis,
  Document,
  Setting,
} from "@element-plus/icons-vue";
import type { NavItem, PullRequestInfo, SummaryItem, RiskFile, ChangedFile, AiSuggestion, Issue, RiskLevel } from "./types/review";
import { normalizeGitHubPrUrl, mapAnalyzeResponse, analyzePR } from "./api/reviewApi";
import AppSidebar from "./components/AppSidebar.vue";
import SearchPanel from "./components/SearchPanel.vue";
import PRInfoCard from "./components/PRInfoCard.vue";
import SummaryCard from "./components/SummaryCard.vue";
import RiskCard from "./components/RiskCard.vue";
import DiffViewer from "./components/DiffViewer.vue";
import AISummaryPanel from "./components/AISummaryPanel.vue";

const prUrl = ref("https://github.com/octocat/Hello-World/pull/6");
const isAnalyzing = ref(false);
const analysisStatus = ref<"idle" | "analyzing" | "completed" | "failed">("completed");
const analysisDuration = ref(1.8);
const analyzedUrl = ref(prUrl.value);
const activeSummaryTag = ref("全部");
const selectedRiskPath = ref("service/payment_service.py");
const backendWarning = ref("");
const errorMessage = ref("");

const navItems: NavItem[] = [
  { label: "PR 分析", icon: DataAnalysis, active: true },
  { label: "历史分析", icon: Clock },
  { label: "报告中心", icon: Document },
  { label: "设置中心", icon: Setting },
];

const pullRequest = ref<PullRequestInfo>({
  repository: "org/ecommerce-platform",
  visibility: "公开仓库",
  title: "feat: 支付回调重试机制与订单状态流转重构",
  description: "实现支付回调失败重试机制，优化订单状态流转逻辑，提升系统稳定性。",
  author: "李明",
  sourceBranch: "feature/payment-retry",
  targetBranch: "develop",
  createdAt: "2026-05-20 14:32",
  updatedAt: "2026-05-21 09:15",
  state: "Open",
  changedFiles: 18,
  additions: 523,
  deletions: 312,
});

const summaryItems = ref<SummaryItem[]>([
  { text: "新增支付回调重试机制，支持最多 3 次重试", tag: "新增功能", tone: "green" },
  { text: "重构订单状态流转逻辑，引入新的状态更新方法", tag: "重构", tone: "blue" },
  { text: "修改 payment_service.py 的支付成功回调处理流程", tag: "重构", tone: "blue" },
  { text: "补充订单不存在时的异常处理逻辑", tag: "优化", tone: "orange" },
  { text: "新增相关单元测试覆盖重试和回调失败场景", tag: "测试", tone: "violet" },
]);

const riskFiles = ref<RiskFile[]>([
  { path: "service/payment_service.py", count: 6 },
  { path: "controller/order_controller.java", count: 4 },
  { path: "repository/order_repository.py", count: 2 },
]);

const changedFiles: ChangedFile[] = [
  { folder: "service", name: "payment_service.py", alerts: 6, active: true },
  { folder: "service", name: "order_service.py", alerts: 3 },
  { folder: "controller", name: "order_controller.java", alerts: 4 },
  { folder: "controller", name: "payment_controller.py", alerts: 2 },
  { folder: "repository", name: "order_repository.py", alerts: 2 },
  { folder: "test", name: "test_payment_retry.py", alerts: 1 },
  { folder: "test", name: "test_order_service.py", alerts: 1 },
];

const codeLines = [
  { line: 118, mark: " ", code: "@@ -118,15 +118,18 @@ def handle_payment_callback(self, request):" },
  { line: 119, mark: " ", code: "# 验证回调签名" },
  { line: 120, mark: " ", code: "if not self._verify_signature(request):" },
  { line: 121, mark: " ", code: "    return self._error_response(\"invalid signature\")" },
  { line: 122, mark: "-", code: "order_id = request.json[\"order_id\"]" },
  { line: 123, mark: "-", code: "payment_id = request.json[\"payment_id\"]" },
  { line: 124, mark: "-", code: "amount = request.json[\"amount\"]" },
  { line: 126, mark: "+", code: "order_id = request.json.get(\"order_id\")" },
  { line: 127, mark: "+", code: "payment_id = request.json.get(\"payment_id\")" },
  { line: 128, mark: "+", code: "amount = request.json.get(\"amount\")" },
  { line: 130, mark: "+", code: "if not order_id or not payment_id:" },
  { line: 131, mark: "+", code: "    return self._error_response(\"missing required parameters\")" },
  { line: 134, mark: " ", code: "order = self.order_service.get_order(order_id)" },
  { line: 135, mark: " ", code: "if not order:" },
  { line: 136, mark: " ", code: "    return self._error_response(\"order not found\")" },
];

const aiSuggestions = ref<AiSuggestion[]>([
  {
    level: "高风险",
    title: "参数获取可能导致 KeyError 异常",
    line: "第122-124行",
    description: "直接读取 request.json 字段会在参数缺失时抛异常，建议统一使用 get 并增加必要性校验。",
  },
  {
    level: "中风险",
    title: "金额参数校验可以更完善",
    line: "第128-129行",
    description: "当前仅做非空校验，建议补充数值格式、精度和币种一致性检查。",
  },
]);

const topIssues = ref<Issue[]>([
  { title: "支付回调可能重复提交", file: "payment_service.py:128", level: "high" },
  { title: "订单状态并发更新风险", file: "order_controller.java:276", level: "high" },
  { title: "权限校验可能缺失", file: "payment_controller.py:88", level: "medium" },
]);

const riskTotal = computed(() => riskFiles.value.reduce((total, file) => total + file.count, 0));
const summaryTags = computed(() => ["全部", ...Array.from(new Set(summaryItems.value.map((item) => item.tag)))]);
const filteredSummaryItems = computed(() => {
  if (activeSummaryTag.value === "全部") return summaryItems.value;
  return summaryItems.value.filter((item) => item.tag === activeSummaryTag.value);
});

const analysisStatusText = computed(() => {
  if (analysisStatus.value === "analyzing") return "正在获取 PR 变更并进行 AI 分析...";
  if (analysisStatus.value === "failed") return errorMessage.value || "分析失败，请稍后重试";
  return "分析完成";
});

const riskLabel: Record<RiskLevel, string> = {
  high: "高风险",
  medium: "中风险",
  low: "低风险",
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "/api/v1";
const reviewApiToken = import.meta.env.VITE_REVIEW_API_TOKEN || "";

const handleAnalyze = async () => {
  const nextUrl = normalizeGitHubPrUrl(prUrl.value);

  if (!nextUrl) {
    errorMessage.value = "请输入正确的 GitHub Pull Request 链接";
    analysisStatus.value = "failed";
    ElMessage.warning(errorMessage.value);
    return;
  }

  isAnalyzing.value = true;
  analysisStatus.value = "analyzing";
  errorMessage.value = "";
  analyzedUrl.value = nextUrl;
  prUrl.value = nextUrl;
  backendWarning.value = "";

  try {
    const data = await analyzePR(nextUrl, apiBaseUrl, reviewApiToken);
    const mapped = mapAnalyzeResponse(data);

    pullRequest.value = { ...pullRequest.value, ...mapped.pullRequest } as PullRequestInfo;
    summaryItems.value = mapped.summaryItems;
    riskFiles.value = mapped.riskFiles;
    if (mapped.riskFiles[0]) selectedRiskPath.value = mapped.riskFiles[0].path;
    topIssues.value = mapped.topIssues;
    aiSuggestions.value = mapped.aiSuggestions;
    activeSummaryTag.value = "全部";
    backendWarning.value = mapped.warnings;
    analysisDuration.value = data.durationMs / 1000;
    analysisStatus.value = "completed";
    ElMessage.success("后端分析完成");
  } catch (error) {
    analysisStatus.value = "failed";
    const message = error instanceof Error ? error.message : "后端请求失败";
    errorMessage.value = `分析失败：${message}`;
    ElMessage.error(errorMessage.value);
  } finally {
    isAnalyzing.value = false;
  }
};
</script>

<template>
  <div class="app-shell">
    <AppSidebar :nav-items="navItems" />

    <main class="workspace">
      <section class="hero-row">
        <SearchPanel
          :pr-url="prUrl"
          :is-analyzing="isAnalyzing"
          :analysis-status="analysisStatus"
          :analysis-status-text="analysisStatusText"
          :analysis-duration="analysisDuration"
          :analyzed-url="analyzedUrl"
          :backend-warning="backendWarning"
          @analyze="handleAnalyze"
          @update:pr-url="prUrl = $event"
        />
        <PRInfoCard :pull-request="pullRequest" />
      </section>

      <section class="dashboard-grid">
        <div class="left-column">
          <SummaryCard
            :summary-items="filteredSummaryItems"
            :summary-tags="summaryTags"
            :active-summary-tag="activeSummaryTag"
            @filter="activeSummaryTag = $event"
          />
          <RiskCard
            :risk-files="riskFiles"
            :risk-total="riskTotal"
            :selected-risk-path="selectedRiskPath"
            @select-file="selectedRiskPath = $event"
          />
        </div>

        <div class="center-column">
          <DiffViewer
            :code-lines="codeLines"
            :changed-files="changedFiles"
            :ai-suggestions="aiSuggestions"
          />
        </div>

        <aside class="right-column">
          <AISummaryPanel :top-issues="topIssues" :risk-label="riskLabel" />
        </aside>
      </section>
    </main>
  </div>
</template>

<style scoped lang="scss">
@use "./styles/variables" as *;

.app-shell {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: $page;
}

.workspace {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 12px;
  min-width: 0;
  height: 100%;
  padding: 18px 18px 16px;
  overflow: hidden;
}

.hero-row {
  display: grid;
  grid-template-columns: minmax(320px, 30%) minmax(0, 70%);
  gap: 16px;
  min-height: 126px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(230px, 20%) minmax(0, 60%) minmax(260px, 20%);
  gap: 16px;
  min-height: 0;
}

.left-column,
.center-column {
  display: grid;
  gap: 16px;
  min-height: 0;
}

.left-column {
  grid-template-rows: 352px minmax(0, 1fr);
}

.center-column {
  grid-template-rows: minmax(0, 1fr);
}

.right-column {
  min-height: 0;
}

@media (max-width: 1440px) {
  .app-shell {
    grid-template-columns: 236px minmax(0, 1fr);
  }

  .workspace {
    padding: 14px;
  }

  .dashboard-grid {
    grid-template-columns: 230px minmax(0, 1fr) 260px;
  }
}

@media (max-width: 1180px) {
  html,
  body,
  #app {
    overflow: auto;
  }

  .app-shell,
  .workspace {
    height: auto;
    min-height: 100vh;
    overflow: visible;
  }

  .hero-row,
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}
</style>
