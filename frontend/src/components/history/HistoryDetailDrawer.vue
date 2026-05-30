<script setup lang="ts">
import type { FeedbackRating, ReviewRecordDetail } from "../../types/history";
import { riskLabel, riskTotal } from "../../composables/useReviewHistory";

defineProps<{
  visible: boolean;
  loading: boolean;
  record: ReviewRecordDetail | null;
  feedbackState: Record<string, FeedbackRating>;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  feedback: [riskIndex: number, rating: FeedbackRating];
}>();
</script>

<template>
  <el-drawer
    :model-value="visible"
    title="评审详情"
    size="46%"
    @update:model-value="emit('update:visible', $event)"
  >
    <div v-loading="loading" class="record-detail">
      <template v-if="record">
        <section class="detail-summary">
          <h3>{{ record.pr_title || "未命名 PR" }}</h3>
          <p>{{ record.result_json?.analysis.summary.overview || "暂无总结" }}</p>
          <div>
            <el-tag>{{ record.owner }}/{{ record.repo }}</el-tag>
            <el-tag type="success">{{ record.file_count }} 个文件</el-tag>
            <el-tag type="warning">{{ riskTotal(record) }} 个风险</el-tag>
          </div>
        </section>

        <section class="detail-risks">
          <h4>AI 建议反馈</h4>
          <article
            v-for="(risk, index) in record.result_json?.analysis.risks || []"
            :key="`${risk.file}-${index}`"
            class="risk-item"
          >
            <div class="risk-head">
              <el-tag :type="risk.severity === 'high' ? 'danger' : risk.severity === 'medium' ? 'warning' : 'success'">
                {{ riskLabel[risk.severity] }}
              </el-tag>
              <span>{{ risk.file }}{{ risk.line ? `:${risk.line}` : "" }}</span>
            </div>
            <strong>{{ risk.issue }}</strong>
            <p>{{ risk.suggestion }}</p>
            <div class="feedback-actions">
              <el-button size="small" @click="emit('feedback', index, 'helpful')">有用</el-button>
              <el-button size="small" @click="emit('feedback', index, 'not_helpful')">无用</el-button>
              <el-button size="small" @click="emit('feedback', index, 'false_positive')">误报</el-button>
              <em v-if="feedbackState[`${record.id}-${index}`]">已反馈</em>
            </div>
          </article>
          <p v-if="(record.result_json?.analysis.risks || []).length === 0" class="empty-detail">暂无可反馈的风险建议</p>
        </section>
      </template>
    </div>
  </el-drawer>
</template>

<style scoped lang="scss">
@use "../../styles/variables" as *;

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
</style>
