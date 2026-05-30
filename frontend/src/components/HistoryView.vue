<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Delete, Refresh, Search, View } from "@element-plus/icons-vue";
import {
  deleteReviewRecord,
  fetchReviewRecordDetail,
  fetchReviewRecords,
  submitReviewFeedback,
} from "../api/historyApi";
import type { FeedbackRating, ReviewRecord, ReviewRecordDetail, RiskLevel } from "../types/review";

const props = defineProps<{
  apiBaseUrl: string;
  accessToken: string;
}>();

const emit = defineEmits<{
  "require-login": [];
}>();

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

const statusOptions = [
  { label: "全部状态", value: "" },
  { label: "已完成", value: "completed" },
  { label: "分析中", value: "pending" },
  { label: "失败", value: "failed" },
];

const riskLabel: Record<RiskLevel, string> = {
  high: "高风险",
  medium: "中风险",
  low: "低风险",
};

const statusLabel: Record<string, string> = {
  completed: "已完成",
  pending: "分析中",
  failed: "失败",
};

const selectedRisks = computed(() => selectedRecord.value?.result_json?.analysis.risks || []);

const formatTime = (value: string | null) => {
  if (!value) return "-";
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
};

const riskTotal = (record: ReviewRecord) => {
  const counts = record.risk_counts || {};
  return (counts.high || 0) + (counts.medium || 0) + (counts.low || 0);
};

const loadRecords = async () => {
  if (!props.accessToken) {
    emit("require-login");
    return;
  }

  loading.value = true;
  try {
    const data = await fetchReviewRecords(props.apiBaseUrl, props.accessToken, {
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
    if (message.includes("401") || message.includes("token")) emit("require-login");
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
    selectedRecord.value = await fetchReviewRecordDetail(props.apiBaseUrl, props.accessToken, record.id);
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

  await deleteReviewRecord(props.apiBaseUrl, props.accessToken, record.id);
  ElMessage.success("已删除");
  await loadRecords();
};

const sendFeedback = async (riskIndex: number, rating: FeedbackRating) => {
  if (!selectedRecord.value) return;

  const key = `${selectedRecord.value.id}-${riskIndex}`;
  await submitReviewFeedback(props.apiBaseUrl, props.accessToken, selectedRecord.value.id, riskIndex, rating);
  feedbackState.value[key] = rating;
  ElMessage.success("反馈已提交");
};

watch([page, pageSize], () => {
  void loadRecords();
});

onMounted(() => {
  void loadRecords();
});
</script>

<template>
  <section class="history-view">
    <header class="history-head">
      <div>
        <h2>历史分析</h2>
        <p>查看已持久化的评审记录，按仓库和状态快速筛选。</p>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadRecords">刷新</el-button>
    </header>

    <div class="history-filters">
      <el-select v-model="statusFilter" class="filter-status" @change="page = 1">
        <el-option
          v-for="option in statusOptions"
          :key="option.value"
          :label="option.label"
          :value="option.value"
        />
      </el-select>
      <el-input v-model="ownerFilter" :prefix-icon="Search" placeholder="Owner" clearable @keyup.enter="loadRecords" />
      <el-input v-model="repoFilter" :prefix-icon="Search" placeholder="Repo" clearable @keyup.enter="loadRecords" />
      <el-button class="primary-button" type="primary" :icon="Search" @click="page = 1; loadRecords()">筛选</el-button>
      <el-button @click="resetFilters">重置</el-button>
    </div>

    <div class="history-table-wrap">
      <el-table v-loading="loading" :data="records" height="100%" row-key="id">
        <el-table-column prop="pr_title" label="PR" min-width="260">
          <template #default="{ row }">
            <div class="pr-cell">
              <strong>{{ row.pr_title || row.pr_url }}</strong>
              <span>{{ row.owner || "-" }}/{{ row.repo || "-" }} #{{ row.pr_number || "-" }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'">
              {{ statusLabel[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="风险" width="160">
          <template #default="{ row }">
            <div class="risk-counts">
              <span class="high">{{ row.risk_counts?.high || 0 }}</span>
              <span class="medium">{{ row.risk_counts?.medium || 0 }}</span>
              <span class="low">{{ row.risk_counts?.low || 0 }}</span>
              <strong>{{ riskTotal(row) }}</strong>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="file_count" label="文件" width="90" />
        <el-table-column label="耗时" width="100">
          <template #default="{ row }">{{ row.duration_ms ? `${(row.duration_ms / 1000).toFixed(1)}s` : "-" }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button :icon="View" size="small" text @click="openDetail(row)">详情</el-button>
            <el-button :icon="Delete" size="small" text type="danger" @click="removeRecord(row)" />
          </template>
        </el-table-column>
      </el-table>
    </div>

    <footer class="history-pagination">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        layout="total, sizes, prev, pager, next"
        :page-sizes="[10, 20, 50]"
        :total="total"
      />
    </footer>

    <el-drawer v-model="detailVisible" title="评审详情" size="46%">
      <div v-loading="detailLoading" class="record-detail">
        <template v-if="selectedRecord">
          <section class="detail-summary">
            <h3>{{ selectedRecord.pr_title || "未命名 PR" }}</h3>
            <p>{{ selectedRecord.result_json?.analysis.summary.overview || "暂无总结" }}</p>
            <div>
              <el-tag>{{ selectedRecord.owner }}/{{ selectedRecord.repo }}</el-tag>
              <el-tag type="success">{{ selectedRecord.file_count }} 个文件</el-tag>
              <el-tag type="warning">{{ riskTotal(selectedRecord) }} 个风险</el-tag>
            </div>
          </section>

          <section class="detail-risks">
            <h4>AI 建议反馈</h4>
            <article v-for="(risk, index) in selectedRisks" :key="`${risk.file}-${index}`" class="risk-item">
              <div class="risk-head">
                <el-tag :type="risk.severity === 'high' ? 'danger' : risk.severity === 'medium' ? 'warning' : 'success'">
                  {{ riskLabel[risk.severity] }}
                </el-tag>
                <span>{{ risk.file }}{{ risk.line ? `:${risk.line}` : "" }}</span>
              </div>
              <strong>{{ risk.issue }}</strong>
              <p>{{ risk.suggestion }}</p>
              <div class="feedback-actions">
                <el-button size="small" @click="sendFeedback(index, 'helpful')">有用</el-button>
                <el-button size="small" @click="sendFeedback(index, 'not_helpful')">无用</el-button>
                <el-button size="small" @click="sendFeedback(index, 'false_positive')">误报</el-button>
                <em v-if="feedbackState[`${selectedRecord.id}-${index}`]">已反馈</em>
              </div>
            </article>
            <p v-if="selectedRisks.length === 0" class="empty-detail">暂无可反馈的风险建议</p>
          </section>
        </template>
      </div>
    </el-drawer>
  </section>
</template>

<style scoped lang="scss">
@use "../styles/variables" as *;

.history-view {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  gap: 14px;
  min-height: 0;
  height: 100%;
}

.history-head,
.history-filters,
.history-table-wrap,
.history-pagination {
  border: 1px solid $border;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(30, 41, 59, 0.04);
}

.history-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;

  h2,
  p {
    margin: 0;
  }

  h2 {
    color: $text;
    font-size: 20px;
    font-weight: 900;
  }

  p {
    margin-top: 6px;
    color: $muted;
    font-size: 13px;
  }
}

.history-filters {
  display: grid;
  grid-template-columns: 150px 180px 180px auto auto minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  padding: 14px;
}

.filter-status {
  width: 150px;
}

.primary-button {
  border: 0;
  background: $primary-gradient;
}

.history-table-wrap {
  min-height: 0;
  overflow: hidden;
}

.history-pagination {
  display: flex;
  justify-content: flex-end;
  padding: 10px 14px;
}

.pr-cell {
  display: grid;
  gap: 4px;
  min-width: 0;

  strong,
  span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  strong {
    color: $text;
    font-size: 13px;
  }

  span {
    color: $soft;
    font-size: 12px;
  }
}

.risk-counts {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;

  span,
  strong {
    font-weight: 800;
  }

  .high { color: $danger; }
  .medium { color: $warning; }
  .low { color: $primary; }
}

.record-detail {
  min-height: 240px;
}

.detail-summary {
  display: grid;
  gap: 10px;
  padding-bottom: 18px;
  border-bottom: 1px solid $line;

  h3,
  p {
    margin: 0;
  }

  h3 {
    color: $text;
    font-size: 18px;
  }

  p {
    color: $muted;
    line-height: 1.7;
  }

  div {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
}

.detail-risks {
  display: grid;
  gap: 12px;
  padding-top: 18px;

  h4 {
    margin: 0;
    color: $text;
    font-size: 15px;
  }
}

.risk-item {
  display: grid;
  gap: 9px;
  padding: 14px;
  border: 1px solid $line;
  border-radius: 10px;
  background: #fbfdff;

  strong,
  p {
    margin: 0;
  }

  strong {
    color: $text;
    font-size: 14px;
  }

  p {
    color: $muted;
    line-height: 1.65;
  }
}

.risk-head,
.feedback-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.risk-head span,
.feedback-actions em {
  color: $soft;
  font-size: 12px;
  font-style: normal;
}

.empty-detail {
  margin: 0;
  color: $soft;
  font-size: 13px;
}

@media (max-width: 1180px) {
  .history-view {
    height: auto;
  }

  .history-filters {
    grid-template-columns: 1fr;
  }

  .filter-status {
    width: 100%;
  }
}
</style>
