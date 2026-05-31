import { ref } from "vue";
import { ElMessage } from "element-plus";
import { fetchReviewStats } from "../api/statsApi";
import type { AgentFeedbackStats, ReviewStatsResponse } from "../types/reviewStats";

export const useReviewStats = (
  getApiBaseUrl: () => string,
  getAccessToken: () => string,
  requireLogin: () => void,
) => {
  const stats = ref<ReviewStatsResponse | null>(null);
  const loading = ref(false);

  const ensureToken = () => {
    const token = getAccessToken();
    if (!token) {
      requireLogin();
      return "";
    }
    return token;
  };

  const loadStats = async () => {
    const token = ensureToken();
    if (!token) return;

    loading.value = true;
    try {
      stats.value = await fetchReviewStats(getApiBaseUrl(), token);
    } catch (error) {
      const message = error instanceof Error ? error.message : "统计数据加载失败";
      ElMessage.error(message);
    } finally {
      loading.value = false;
    }
  };

  const agentLabel = (agent: string) => {
    const map: Record<string, string> = {
      "安全": "安全专家",
      "性能": "性能专家",
      "风格": "风格专家",
      "通用": "通用",
    };
    return map[agent] || agent;
  };

  const percent = (value: number) => `${(value * 100).toFixed(1)}%`;

  return {
    stats,
    loading,
    loadStats,
    agentLabel,
    percent,
  };
};

export type { AgentFeedbackStats };
