<script setup lang="ts">
import { computed, ref } from "vue";
import {
  AlertTriangle,
  CheckCircle2,
  Clipboard,
  Code2,
  FileSearch,
  Filter,
  Loader2,
  Search,
  ShieldCheck
} from "lucide-vue-next";
import { analyzePullRequest } from "./api/reviewApi";
import type { AnalyzeResponse, RiskItem, Severity } from "./types/review";

const prUrl = ref("");
const isLoading = ref(false);
const errorMessage = ref("");
const selectedSeverity = ref<"all" | Severity>("all");
const copied = ref(false);
const result = ref<AnalyzeResponse | null>(null);

const severityOptions: Array<{ value: "all" | Severity; label: string }> = [
  { value: "all", label: "全部" },
  { value: "high", label: "高风险" },
  { value: "medium", label: "中风险" },
  { value: "low", label: "低风险" }
];

const filteredRisks = computed(() => {
  const risks = result.value?.analysis.risks ?? [];
  if (selectedSeverity.value === "all") {
    return risks;
  }
  return risks.filter((risk) => risk.severity === selectedSeverity.value);
});

const riskScore = computed(() => {
  const metrics = result.value?.analysis.metrics;
  if (!metrics) {
    return 0;
  }
  return metrics.highRiskCount * 5 + metrics.mediumRiskCount * 3 + metrics.lowRiskCount;
});

const riskLevelLabel = computed(() => {
  if (riskScore.value >= 8) {
    return "需要重点复核";
  }
  if (riskScore.value >= 4) {
    return "建议谨慎合并";
  }
  return "风险较低";
});

async function handleAnalyze() {
  errorMessage.value = "";
  copied.value = false;
  isLoading.value = true;

  try {
    result.value = await analyzePullRequest(prUrl.value);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "分析失败，请稍后重试。";
  } finally {
    isLoading.value = false;
  }
}

function severityLabel(severity: Severity) {
  const labels: Record<Severity, string> = {
    high: "高风险",
    medium: "中风险",
    low: "低风险"
  };
  return labels[severity];
}

function suggestionLabel(type: string) {
  const labels: Record<string, string> = {
    must_fix: "必须修复",
    should_fix: "建议修复",
    nice_to_have: "可选优化"
  };
  return labels[type] ?? type;
}

function formatDuration(durationMs: number) {
  if (durationMs < 1000) {
    return `${durationMs} ms`;
  }
  return `${(durationMs / 1000).toFixed(1)} s`;
}

function buildMarkdown() {
  if (!result.value) {
    return "";
  }

  const { pr, analysis, durationMs } = result.value;
  const riskLines = analysis.risks
    .map((risk) => {
      const line = risk.line ? `:${risk.line}` : "";
      return [
        `### ${severityLabel(risk.severity)} - ${risk.category}`,
        "",
        `- 位置：\`${risk.file}${line}\``,
        `- 问题：${risk.issue}`,
        `- 影响：${risk.impact}`,
        `- 建议：${risk.suggestion}`,
        `- 置信度：${risk.confidence}`
      ].join("\n");
    })
    .join("\n\n");

  const suggestionLines = analysis.suggestions
    .map((suggestion) => {
      return `- [${suggestionLabel(suggestion.type)}] \`${suggestion.file}\`：${suggestion.comment}`;
    })
    .join("\n");

  return [
    "## AI Review Summary",
    "",
    `PR：${pr.title}`,
    `地址：${pr.url}`,
    `分析耗时：${formatDuration(durationMs)}`,
    "",
    "### 变更概览",
    "",
    analysis.summary.overview,
    "",
    "### 影响范围",
    "",
    ...analysis.summary.impact.map((item) => `- ${item}`),
    "",
    "## Risk Findings",
    "",
    riskLines || "未发现明确风险。",
    "",
    "## Suggestions",
    "",
    suggestionLines || "暂无建议。"
  ].join("\n");
}

async function copyMarkdown() {
  if (!result.value) {
    return;
  }

  await navigator.clipboard.writeText(buildMarkdown());
  copied.value = true;
  window.setTimeout(() => {
    copied.value = false;
  }, 1800);
}

function riskLocation(risk: RiskItem) {
  return risk.line ? `${risk.file}:${risk.line}` : risk.file;
}
</script>

<template>
  <main class="app-shell">
    <section class="workspace">
      <header class="topbar">
        <div>
          <p class="eyebrow">AI Code Review</p>
          <h1>Pull Request 智能评审</h1>
        </div>
        <div class="status-pill">
          <ShieldCheck :size="16" />
          <span>MVP Preview</span>
        </div>
      </header>

      <section class="review-console" aria-label="PR 分析控制台">
        <div class="input-panel">
          <div>
            <h2>指定 GitHub PR</h2>
            <p>输入 PR 地址后开始分析。后端未启动时会展示内置示例结果，便于调试界面。</p>
          </div>
          <form class="pr-form" @submit.prevent="handleAnalyze">
            <label class="sr-only" for="pr-url">GitHub PR URL</label>
            <div class="input-wrap">
              <Search :size="18" />
              <input
                id="pr-url"
                v-model="prUrl"
                type="url"
                placeholder="https://github.com/owner/repo/pull/123"
              />
            </div>
            <button class="primary-button" type="submit" :disabled="isLoading">
              <Loader2 v-if="isLoading" :size="18" class="spin" />
              <FileSearch v-else :size="18" />
              <span>{{ isLoading ? "分析中" : "开始分析" }}</span>
            </button>
          </form>
          <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
        </div>

        <div class="score-panel">
          <span class="score-label">当前评估</span>
          <strong>{{ result ? riskLevelLabel : "等待分析" }}</strong>
          <p>{{ result ? `风险评分 ${riskScore}，共分析 ${result.analysis.metrics.analyzedFileCount} 个文件` : "输入 PR 后生成总结、风险和建议。" }}</p>
        </div>
      </section>

      <section v-if="!result" class="empty-state">
        <Code2 :size="34" />
        <h2>准备开始一次 AI 辅助 Review</h2>
        <p>页面会聚合 PR 摘要、风险代码、置信度和可复制的 Review 建议。</p>
      </section>

      <template v-else>
        <section class="metric-grid" aria-label="风险统计">
          <article class="metric-card danger">
            <span>高风险</span>
            <strong>{{ result.analysis.metrics.highRiskCount }}</strong>
          </article>
          <article class="metric-card warning">
            <span>中风险</span>
            <strong>{{ result.analysis.metrics.mediumRiskCount }}</strong>
          </article>
          <article class="metric-card calm">
            <span>低风险</span>
            <strong>{{ result.analysis.metrics.lowRiskCount }}</strong>
          </article>
          <article class="metric-card neutral">
            <span>分析耗时</span>
            <strong>{{ formatDuration(result.durationMs) }}</strong>
          </article>
        </section>

        <section class="summary-section">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Summary</p>
              <h2>{{ result.pr.title }}</h2>
            </div>
            <button class="secondary-button" type="button" @click="copyMarkdown">
              <Clipboard :size="17" />
              <span>{{ copied ? "已复制" : "复制报告" }}</span>
            </button>
          </div>
          <p class="summary-copy">{{ result.analysis.summary.overview }}</p>
          <div class="tag-row">
            <span v-for="module in result.analysis.summary.changedModules" :key="module" class="tag">
              {{ module }}
            </span>
          </div>
          <div class="impact-list">
            <span v-for="item in result.analysis.summary.impact" :key="item">{{ item }}</span>
          </div>
        </section>

        <section class="content-grid">
          <section class="panel">
            <div class="section-heading compact">
              <div>
                <p class="eyebrow">Risk Findings</p>
                <h2>风险代码识别</h2>
              </div>
              <div class="filter-bar" aria-label="风险筛选">
                <Filter :size="16" />
                <button
                  v-for="option in severityOptions"
                  :key="option.value"
                  type="button"
                  :class="{ active: selectedSeverity === option.value }"
                  @click="selectedSeverity = option.value"
                >
                  {{ option.label }}
                </button>
              </div>
            </div>

            <div class="risk-list">
              <article
                v-for="risk in filteredRisks"
                :key="`${risk.file}-${risk.line ?? risk.issue}`"
                class="risk-card"
                :class="risk.severity"
              >
                <div class="risk-card-head">
                  <span class="severity-badge">{{ severityLabel(risk.severity) }}</span>
                  <code>{{ riskLocation(risk) }}</code>
                </div>
                <h3>{{ risk.issue }}</h3>
                <p>{{ risk.impact }}</p>
                <div class="recommendation">
                  <CheckCircle2 :size="16" />
                  <span>{{ risk.suggestion }}</span>
                </div>
                <div class="confidence">
                  <span>置信度</span>
                  <meter min="0" max="1" :value="risk.confidence"></meter>
                  <strong>{{ Math.round(risk.confidence * 100) }}%</strong>
                </div>
              </article>
            </div>
          </section>

          <aside class="panel">
            <div class="section-heading compact">
              <div>
                <p class="eyebrow">Review</p>
                <h2>建议清单</h2>
              </div>
            </div>
            <div class="suggestion-list">
              <article
                v-for="suggestion in result.analysis.suggestions"
                :key="`${suggestion.file}-${suggestion.comment}`"
                class="suggestion-item"
              >
                <span :class="['suggestion-type', suggestion.type]">
                  {{ suggestionLabel(suggestion.type) }}
                </span>
                <code>{{ suggestion.file }}</code>
                <p>{{ suggestion.comment }}</p>
              </article>
            </div>
          </aside>
        </section>
      </template>
    </section>
  </main>
</template>
