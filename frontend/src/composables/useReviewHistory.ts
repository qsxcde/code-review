import { computed, onMounted, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  deleteReviewRecord,
  fetchReviewRecordDetail,
  fetchReviewRecords,
  submitReviewFeedback,
} from "../api/historyApi";
import type { FeedbackRating, ReviewRecord, ReviewRecordDetail } from "../types/history";
import type { RiskLevel } from "../types/review";

export const riskLabel: Record<RiskLevel, string> = {
  high: "高风险",
  medium: "中风险",
  low: "低风险",
};

export const statusOptions = [
  { label: "全部状态", value: "" },
  { label: "已完成", value: "completed" },
  { label: "分析中", value: "pending" },
  { label: "失败", value: "failed" },
];

export const statusLabel: Record<string, string> = {
  completed: "已完成",
  pending: "分析中",
  failed: "失败",
};

export const formatHistoryTime = (value: string | null) => {
  if (!value) return "-";
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
};

export const riskTotal = (record: ReviewRecord) => {
  const counts = record.risk_counts || {};
  return (counts.high || 0) + (counts.medium || 0) + (counts.low || 0);
};

export const useReviewHistory = (
  getApiBaseUrl: () => string,
  getAccessToken: () => string,
  requireLogin: () => void,
) => {
  const records = ref<ReviewRecord[]>([]);
  const total = ref(0);
  const page = ref(1);
  const pageSize = ref(10);
  const statusFilter = ref("");
  const ownerFilter = ref("");
  const repoFilter = ref("");
  const loading = ref(false);
  const detailLoading = ref(false);
  const detailVisible = ref(false);
  const selectedRecord = ref<ReviewRecordDetail | null>(null);
  const feedbackState = ref<Record<string, FeedbackRating>>({});
  const selectedRisks = computed(() => selectedRecord.value?.result_json?.analysis.risks || []);

  const loadRecords = async () => {
    const accessToken = getAccessToken();
    if (!accessToken) {
      requireLogin();
      return;
    }

    loading.value = true;
    try {
      const data = await fetchReviewRecords(getApiBaseUrl(), accessToken, {
        page: page.value,
        pageSize: pageSize.value,
        status: statusFilter.value,
        owner: ownerFilter.value.trim(),
        repo: repoFilter.value.trim(),
      });
      records.value = data.items;
      total.value = data.total;
    } catch (error) {
      const message = error instanceof Error ? error.message : "历史记录加载失败";
      ElMessage.error(message);
      if (message.includes("401") || message.includes("token")) requireLogin();
    } finally {
      loading.value = false;
    }
  };

  const resetFilters = () => {
    statusFilter.value = "";
    ownerFilter.value = "";
    repoFilter.value = "";
    page.value = 1;
    void loadRecords();
  };

  const openDetail = async (record: ReviewRecord) => {
    detailVisible.value = true;
    detailLoading.value = true;
    selectedRecord.value = null;

    try {
      selectedRecord.value = await fetchReviewRecordDetail(getApiBaseUrl(), getAccessToken(), record.id);
    } catch (error) {
      const message = error instanceof Error ? error.message : "详情加载失败";
      ElMessage.error(message);
    } finally {
      detailLoading.value = false;
    }
  };

  const removeRecord = async (record: ReviewRecord) => {
    await ElMessageBox.confirm("删除后无法恢复，确认删除这条评审历史吗？", "删除记录", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
    });

    await deleteReviewRecord(getApiBaseUrl(), getAccessToken(), record.id);
    ElMessage.success("已删除");
    await loadRecords();
  };

  const sendFeedback = async (riskIndex: number, rating: FeedbackRating) => {
    if (!selectedRecord.value) return;

    const key = `${selectedRecord.value.id}-${riskIndex}`;
    await submitReviewFeedback(getApiBaseUrl(), getAccessToken(), selectedRecord.value.id, riskIndex, rating);
    feedbackState.value[key] = rating;
    ElMessage.success("反馈已提交");
  };

  watch([page, pageSize], () => {
    void loadRecords();
  });

  onMounted(() => {
    void loadRecords();
  });

  return {
    records,
    total,
    page,
    pageSize,
    statusFilter,
    ownerFilter,
    repoFilter,
    loading,
    detailLoading,
    detailVisible,
    selectedRecord,
    feedbackState,
    selectedRisks,
    loadRecords,
    resetFilters,
    openDetail,
    removeRecord,
    sendFeedback,
  };
};
