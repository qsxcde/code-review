<script setup lang="ts">
import { Promotion, Download } from "@element-plus/icons-vue";
import type { RiskLevel, Issue } from "../types/review";

defineProps<{
  topIssues: Issue[];
  riskLabel: Record<RiskLevel, string>;
}>();
</script>

<template>
  <el-card class="panel ai-summary-card" shadow="never">
    <h3>AI 总结结论</h3>
    <div class="risk-level">
      <span>整体风险等级</span>
      <strong>中等风险</strong>
    </div>
    <div class="risk-metrics">
      <span><strong>47</strong>风险问题</span>
      <span><strong>8</strong>涉及文件</span>
      <span><strong>建议修复后合并</strong>建议合并</span>
    </div>
    <div class="strategy-card">
      <strong>模型与上下文策略</strong>
      <span>模型：GPT-4.1 / DeepSeek-R1 可切换</span>
      <span>上下文：PR Diff + 关联文件 + 历史提交</span>
      <span>扩展：CI 门禁 / IDE 插件 / 团队规则库</span>
    </div>
    <h4>优先处理问题 TOP 3</h4>
    <article v-for="(issue, index) in topIssues" :key="issue.title" class="issue-item">
      <em>{{ index + 1 }}</em>
      <div>
        <strong>{{ issue.title }}</strong>
        <span>{{ issue.file }}</span>
      </div>
      <el-tag :class="`risk-${issue.level}`" size="small">{{ riskLabel[issue.level] }}</el-tag>
    </article>
    <div class="summary-actions">
      <el-button class="primary-button" type="primary" :icon="Promotion">生成完整 Review 报告</el-button>
      <el-button :icon="Download">导出分析结果</el-button>
    </div>
  </el-card>
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
    grid-template-rows: auto auto auto auto auto 1fr;
    gap: 14px;
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

.risk-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;

  span {
    display: grid;
    gap: 6px;
    color: $muted;
    font-size: 11px;
  }

  strong {
    color: $text;
    font-size: 15px;
  }
}

.strategy-card {
  display: grid;
  gap: 6px;
  padding: 12px;
  border: 1px solid $line;
  border-radius: 10px;
  background: #fbfdff;

  strong {
    color: $text;
    font-size: 13px;
  }

  span {
    color: $muted;
    font-size: 11px;
    line-height: 1.45;
  }
}

.issue-item {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 9px 0;
  border-bottom: 1px solid $line;

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
</style>
