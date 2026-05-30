<script setup lang="ts">
import { ref } from "vue";
import { ElMessage } from "element-plus";
import { riskLabel, usePrAnalysis } from "../composables/usePrAnalysis";
import { useReviewReport } from "../composables/useReviewReport";
import SearchPanel from "../components/SearchPanel.vue";
import PRInfoCard from "../components/PRInfoCard.vue";
import SummaryCard from "../components/SummaryCard.vue";
import RiskCard from "../components/RiskCard.vue";
import DiffViewer from "../components/DiffViewer.vue";
import AISummaryPanel from "../components/AISummaryPanel.vue";

const props = defineProps<{
  apiBaseUrl: string;
  accessToken: string;
}>();

const emit = defineEmits<{
  "require-login": [];
  "expire-session": [];
}>();

const analysis = usePrAnalysis(
  props.apiBaseUrl,
  () => props.accessToken,
  () => emit("require-login"),
  () => emit("expire-session"),
);

const reportDialogVisible = ref(false);
const reportMarkdown = ref("");

const { buildReviewReportMarkdown, reportFileName } = useReviewReport({
  currentAnalysis: analysis.currentAnalysis,
  pullRequest: analysis.pullRequest,
  analyzedUrl: analysis.analyzedUrl,
  riskStats: analysis.riskStats,
  summaryItems: analysis.summaryItems,
  topIssues: analysis.topIssues,
  aiSuggestions: analysis.aiSuggestions,
});

const downloadTextFile = (content: string, fileName: string) => {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
};

const handleGenerateReport = () => {
  reportMarkdown.value = buildReviewReportMarkdown();
  reportDialogVisible.value = true;
};

const handleExportResult = () => {
  const markdown = buildReviewReportMarkdown();
  downloadTextFile(markdown, reportFileName());
  ElMessage.success("分析结果已导出");
};

const copyReport = async () => {
  await navigator.clipboard.writeText(reportMarkdown.value);
  ElMessage.success("报告已复制");
};
</script>

<template>
  <main class="workspace">
    <section class="hero-row">
      <SearchPanel
        :pr-url="analysis.prUrl.value"
        :is-analyzing="analysis.isAnalyzing.value"
        :analysis-status="analysis.analysisStatus.value"
        :analysis-status-text="analysis.analysisStatusText.value"
        :analysis-duration="analysis.analysisDuration.value"
        :analyzed-url="analysis.analyzedUrl.value"
        :backend-warning="analysis.backendWarning.value"
        @analyze="analysis.handleAnalyze"
        @update:pr-url="analysis.prUrl.value = $event"
      />
      <PRInfoCard :pull-request="analysis.pullRequest.value" />
    </section>

    <section class="dashboard-grid">
      <div class="left-column">
        <SummaryCard
          :summary-items="analysis.filteredSummaryItems.value"
          :summary-tags="analysis.summaryTags.value"
          :active-summary-tag="analysis.activeSummaryTag.value"
          @filter="analysis.activeSummaryTag.value = $event"
        />
        <RiskCard
          :risk-files="analysis.riskFiles.value"
          :risk-stats="analysis.riskStats.value"
          :selected-risk-path="analysis.selectedRiskPath.value"
        />
      </div>

      <div class="center-column">
        <DiffViewer
          :code-lines="analysis.codeLines.value"
          :changed-files="analysis.changedFiles.value"
          :ai-suggestions="analysis.selectedFileSuggestions.value"
          :selected-file-path="analysis.selectedCodePath.value"
          @select-file="analysis.updateSelectedCodeFile"
        />
      </div>

      <aside class="right-column">
        <AISummaryPanel
          :summary-stats="analysis.aiSummaryStats.value"
          :top-issues="analysis.topIssues.value"
          :risk-label="riskLabel"
          @generate-report="handleGenerateReport"
          @export-result="handleExportResult"
        />
      </aside>
    </section>

    <el-dialog
      v-model="reportDialogVisible"
      class="report-dialog"
      title="完整 Review 报告"
      width="680px"
      append-to-body
    >
      <el-input
        v-model="reportMarkdown"
        type="textarea"
        :rows="18"
        resize="none"
      />
      <template #footer>
        <div class="report-footer">
          <el-button @click="copyReport">复制报告</el-button>
          <el-button class="auth-primary" type="primary" @click="handleExportResult">导出 Markdown</el-button>
        </div>
      </template>
    </el-dialog>
  </main>
</template>
