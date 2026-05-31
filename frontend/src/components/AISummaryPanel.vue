<script setup lang="ts">
import { ref } from "vue";
import { Promotion, Download } from "@element-plus/icons-vue";
import type { RiskLevel, Issue, AiSummaryStats } from "../types/review";

const props = defineProps<{
  summaryStats: AiSummaryStats;
  topIssues: Issue[];
  riskLabel: Record<RiskLevel, string>;
}>();

const emit = defineEmits<{
  "generate-report": [];
  "export-result": [];
}>();

const detailVisible = ref(false);
const selectedIssue = ref<Issue | null>(null);

const openIssueDetail = (issue: Issue) => {
  selectedIssue.value = issue;
  detailVisible.value = true;
};
</script>

<template>
  <el-card class="panel ai-summary-card" shadow="never">
    <h3>AI 总结结论</h3>
    <div class="risk-level" :class="`risk-level-${summaryStats.riskTone}`">
      <span>整体风险等级</span>
      <strong>{{ summaryStats.riskLevel }}</strong>
    </div>
    <div class="risk-metrics">
      <span><strong>{{ summaryStats.riskIssues }}</strong>风险问题</span>
      <span><strong>{{ summaryStats.involvedFiles }}</strong>涉及文件</span>
      <span><strong>{{ summaryStats.mergeAdvice }}</strong>建议合并</span>
    </div>
    <h4>需要处理的问题</h4>
    <div class="issue-list">
      <p v-if="props.topIssues.length === 0" class="empty-issues">暂无需要处理的问题</p>
      <button
        v-for="(issue, index) in props.topIssues"
        :key="`${issue.file}-${issue.title}-${index}`"
        class="issue-item"
        type="button"
        @click="openIssueDetail(issue)"
      >
        <em>{{ index + 1 }}</em>
        <div>
          <strong>{{ issue.title }}</strong>
          <span>{{ issue.file }}</span>
        </div>
        <el-tag :class="`risk-${issue.level}`" size="small">{{ props.riskLabel[issue.level] }}</el-tag>
      </button>
    </div>
    <div class="summary-actions">
      <el-button class="primary-button" type="primary" :icon="Promotion" @click="emit('generate-report')">
        生成完整 Review 报告
      </el-button>
      <el-button :icon="Download" @click="emit('export-result')">导出分析结果</el-button>
    </div>
  </el-card>

  <el-dialog
    v-model="detailVisible"
    class="issue-dialog"
    title="问题详情"
    width="min(640px, 92vw)"
    append-to-body
  >
    <section v-if="selectedIssue" class="issue-detail">
      <div class="issue-detail-meta">
        <el-tag :class="`risk-${selectedIssue.level}`" size="small">
          {{ props.riskLabel[selectedIssue.level] }}
        </el-tag>
        <el-tag v-if="selectedIssue.agentSource" size="small" type="info">{{ selectedIssue.agentSource }}</el-tag>
        <span>{{ selectedIssue.file }}</span>
      </div>
      <h3>{{ selectedIssue.title }}</h3>
      <div v-if="selectedIssue.impact" class="detail-block">
        <strong>具体问题</strong>
        <p>{{ selectedIssue.impact }}</p>
      </div>
      <div v-if="selectedIssue.suggestion" class="detail-block">
        <strong>AI 建议</strong>
        <p>{{ selectedIssue.suggestion }}</p>
      </div>
      <div v-if="selectedIssue.category || selectedIssue.confidence !== undefined" class="issue-detail-foot">
        <span v-if="selectedIssue.category">分类：{{ selectedIssue.category }}</span>
        <span v-if="selectedIssue.confidence !== undefined">置信度：{{ Math.round(selectedIssue.confidence * 100) }}%</span>
      </div>
    </section>
  </el-dialog>
</template>

<style scoped lang="scss">
@use "../styles/variables" as *;

.panel {
  border: 1px solid $border;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(30, 41, 59, 0.04);
}

h3, h4 {
  margin: 0;
  color: $text;
}

h3 { font-size: 15px; font-weight: 800; }
h4 { font-size: 13px; font-weight: 800; }

.ai-summary-card {
  height: 100%;

  :deep(.el-card__body) {
    display: grid;
    grid-template-rows: auto auto auto auto minmax(0, 1fr) auto;
    gap: 12px;
    height: 100%;
    padding: 16px;
  }
}

.risk-level {
  display: grid;
  gap: 10px;
  padding: 18px;
  border-radius: 12px;
  background: #fff7ed;

  span {
    color: $muted;
    font-size: 13px;
  }

  strong {
    color: #ea580c;
    font-size: 20px;
    font-weight: 900;
  }
}

.risk-level-high {
  background: #fff1f2;

  strong {
    color: $danger;
  }
}

.risk-level-medium {
  background: #fff7ed;

  strong {
    color: #ea580c;
  }
}

.risk-level-low {
  background: #ecfdf3;

  strong {
    color: $success;
  }
}

.risk-metrics {
  display: grid;
  grid-template-columns: 0.75fr 0.75fr 1.3fr;
  gap: 8px;

  span {
    display: grid;
    gap: 6px;
    min-width: 0;
    color: $muted;
    font-size: 11px;
  }

  strong {
    color: $text;
    font-size: 15px;
    line-height: 1.25;
  }

  span:last-child strong {
    font-size: 14px;
  }
}

.issue-list {
  min-height: 0;
  overflow: auto;
}

.issue-item {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  width: 100%;
  min-height: 86px;
  padding: 12px 0;
  border: 0;
  border-bottom: 1px solid $line;
  text-align: left;
  background: transparent;
  cursor: pointer;

  &:hover {
    background: #fbfdff;
  }

  em {
    display: grid;
    width: 20px;
    height: 20px;
    place-items: center;
    border-radius: 6px;
    color: $danger;
    font-style: normal;
    font-weight: 800;
    background: #fff1f2;
  }

  div {
    min-width: 0;
  }

  strong,
  span {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  strong {
    color: $text;
    font-size: 13px;
  }

  span {
    margin-top: 4px;
    color: $soft;
    font-size: 12px;
  }
}

.empty-issues {
  margin: 0;
  color: $soft;
  font-size: 12px;
}

.risk-high { color: $danger; background: #fff1f2; }
.risk-medium { color: $warning; background: #fffbeb; }
.risk-low { color: $success; background: #ecfdf3; }

.summary-actions {
  display: grid;
  align-self: end;
  gap: 10px;
}

.primary-button {
  border: 0;
  border-radius: 8px;
  font-weight: 800;
  background: $primary-gradient;
}

.issue-detail {
  display: grid;
  gap: 16px;

  h3,
  p {
    margin: 0;
  }

  h3 {
    color: $text;
    font-size: 18px;
    font-weight: 900;
    line-height: 1.5;
  }
}

.issue-detail-meta,
.issue-detail-foot {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  color: $soft;
  font-size: 12px;
}

.detail-block {
  display: grid;
  gap: 8px;

  strong {
    color: $text;
    font-size: 13px;
  }

  p {
    color: $muted;
    font-size: 14px;
    line-height: 1.8;
    white-space: pre-wrap;
  }
}
</style>
