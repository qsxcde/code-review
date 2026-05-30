<script setup lang="ts">
import { Delete, Refresh, Search, View } from "@element-plus/icons-vue";
import {
  formatHistoryTime,
  riskTotal,
  statusLabel,
  statusOptions,
  useReviewHistory,
} from "../composables/useReviewHistory";
import HistoryDetailDrawer from "./history/HistoryDetailDrawer.vue";

const props = defineProps<{
  apiBaseUrl: string;
  accessToken: string;
}>();

const emit = defineEmits<{
  "require-login": [];
}>();

const {
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
  loadRecords,
  resetFilters,
  openDetail,
  removeRecord,
  sendFeedback,
} = useReviewHistory(
  () => props.apiBaseUrl,
  () => props.accessToken,
  () => emit("require-login"),
);
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
          <template #default="{ row }">{{ formatHistoryTime(row.created_at) }}</template>
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

    <HistoryDetailDrawer
      v-model:visible="detailVisible"
      :loading="detailLoading"
      :record="selectedRecord"
      :feedback-state="feedbackState"
      @feedback="sendFeedback"
    />
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
