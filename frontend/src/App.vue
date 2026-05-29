<script setup lang="ts">
import { computed, ref } from "vue";
import {
  AlertTriangle,
  CheckCircle2,
  Clipboard,
  ExternalLink,
  FileText,
  Loader2,
  Play,
  ShieldAlert,
} from "lucide-vue-next";
import { analyzePullRequest } from "./api/reviewApi";
import type {
  ReviewAnalyzeResponse,
  ReviewSuggestion,
  RiskItem,
  Severity,
  SuggestionType,
} from "./types/review";

const prUrl = ref("https://github.com/fastapi/fastapi/pull/1");
const loading = ref(false);
const errorMessage = ref("");
const copied = ref(false);
const report = ref<ReviewAnalyzeResponse | null>(null);

const canSubmit = computed(() => prUrl.value.trim().length > 0 && !loading.value);

const severityLabel: Record<Severity, string> = {
  high: "高",
  medium: "中",
  low: "低",
};

const suggestionLabel: Record<SuggestionType, string> = {
  must_fix: "必须修复",
  should_fix: "建议修复",
  nice_to_have: "可优化",
};

async function runAnalysis() {
  if (!canSubmit.value) return;

  loading.value = true;
  errorMessage.value = "";
  copied.value = false;

  try {
    report.value = await analyzePullRequest(prUrl.value.trim());
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "分析失败";
  } finally {
    loading.value = false;
  }
}

async function copyMarkdown() {
  if (!report.value) return;
  await navigator.clipboard.writeText(toMarkdown(report.value));
  copied.value = true;
  window.setTimeout(() => {
    copied.value = false;
  }, 1600);
}

function toPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function formatMs(value: number) {
  return value > 1000 ? `${(value / 1000).toFixed(1)}s` : `${value}ms`;
}

function riskClass(severity: Severity) {
  return `risk-${severity}`;
}

function suggestionClass(type: SuggestionType) {
  return `suggestion-${type}`;
}

function riskTitle(risk: RiskItem) {
  return risk.line ? `${risk.file}:${risk.line}` : risk.file;
}

function toMarkdown(data: ReviewAnalyzeResponse) {
  const risks =
    data.analysis.risks.length === 0
      ? "- 暂无明确风险"
      : data.analysis.risks
          .map(
            (risk) =>
              `- [${severityLabel[risk.severity]}] ${risk.file}${
                risk.line ? `:${risk.line}` : ""
              }：${risk.issue}\n  - 影响：${risk.impact}\n  - 建议：${risk.suggestion}\n  - 置信度：${toPercent(risk.confidence)}`,
          )
          .join("\n");

  const suggestions =
    data.analysis.suggestions.length === 0
      ? "- 暂无建议"
      : data.analysis.suggestions
          .map(
            (suggestion: ReviewSuggestion) =>
              `- [${suggestionLabel[suggestion.type]}] ${suggestion.file}：${suggestion.comment}`,
          )
          .join("\n");

  return `# AI Review 报告

## PR
- 标题：${data.pr.title}
- 地址：${data.pr.url}
- 作者：${data.pr.author}
- 分支：${data.pr.headBranch} -> ${data.pr.baseBranch}

## 总结
${data.analysis.summary.overview}

## 影响范围
${data.analysis.summary.impact.map((item) => `- ${item}`).join("\n")}

## 风险
${risks}

## 建议
${suggestions}

## 指标
- 高风险：${data.analysis.metrics.highRiskCount}
- 中风险：${data.analysis.metrics.mediumRiskCount}
- 低风险：${data.analysis.metrics.lowRiskCount}
- 分析文件数：${data.analysis.metrics.analyzedFileCount}
- 耗时：${formatMs(data.durationMs)}
`;
}
</script>

<template>
  <main class="page-shell">
    <section class="workspace">
      <header class="topbar">
        <div>
          <p class="eyebrow">AI Code Review</p>
          <h1>Pull Request 审查工作台</h1>
        </div>
        <div class="status-pill">
          <CheckCircle2 :size="16" />
          FastAPI 已接入
        </div>
      </header>

      <form class="input-band" @submit.prevent="runAnalysis">
        <label class="input-label" for="pr-url">GitHub PR URL</label>
        <div class="input-row">
          <input
            id="pr-url"
            v-model="prUrl"
            type="url"
            placeholder="https://github.com/owner/repo/pull/123"
            autocomplete="off"
          />
          <button class="primary-button" type="submit" :disabled="!canSubmit">
            <Loader2 v-if="loading" class="spin" :size="18" />
            <Play v-else :size="18" />
            <span>{{ loading ? "分析中" : "开始分析" }}</span>
          </button>
        </div>
        <p v-if="errorMessage" class="error-text">
          <AlertTriangle :size="16" />
          {{ errorMessage }}
        </p>
      </form>

      <section v-if="loading" class="loading-panel">
        <Loader2 class="spin" :size="26" />
        <div>
          <h2>正在生成审查报告</h2>
          <p>正在获取 PR 变更、构建上下文并调用模型。</p>
        </div>
      </section>

      <section v-else-if="report" class="report-layout">
        <aside class="summary-panel">
          <div class="panel-heading">
            <FileText :size="18" />
            <span>PR 信息</span>
          </div>
          <h2>{{ report.pr.title }}</h2>
          <a class="external-link" :href="report.pr.url" target="_blank" rel="noreferrer">
            {{ report.pr.owner }}/{{ report.pr.repo }} #{{ report.pr.number }}
            <ExternalLink :size="15" />
          </a>
          <dl class="meta-list">
            <div>
              <dt>作者</dt>
              <dd>{{ report.pr.author }}</dd>
            </div>
            <div>
              <dt>分支</dt>
              <dd>{{ report.pr.headBranch }} -> {{ report.pr.baseBranch }}</dd>
            </div>
            <div>
              <dt>耗时</dt>
              <dd>{{ formatMs(report.durationMs) }}</dd>
            </div>
          </dl>

          <div class="metrics-grid">
            <div class="metric high">
              <strong>{{ report.analysis.metrics.highRiskCount }}</strong>
              <span>高风险</span>
            </div>
            <div class="metric medium">
              <strong>{{ report.analysis.metrics.mediumRiskCount }}</strong>
              <span>中风险</span>
            </div>
            <div class="metric low">
              <strong>{{ report.analysis.metrics.lowRiskCount }}</strong>
              <span>低风险</span>
            </div>
            <div class="metric">
              <strong>{{ report.analysis.metrics.analyzedFileCount }}</strong>
              <span>文件</span>
            </div>
          </div>

          <button class="secondary-button" type="button" @click="copyMarkdown">
            <Clipboard :size="17" />
            <span>{{ copied ? "已复制" : "复制 Markdown" }}</span>
          </button>
        </aside>

        <section class="content-panel">
          <div class="section-block">
            <div class="panel-heading">
              <ShieldAlert :size="18" />
              <span>审查总结</span>
            </div>
            <p class="overview">{{ report.analysis.summary.overview }}</p>
            <div class="tag-row">
              <span v-for="module in report.analysis.summary.changedModules" :key="module">
                {{ module }}
              </span>
            </div>
          </div>

          <div class="section-block">
            <h2>影响范围</h2>
            <ul class="impact-list">
              <li v-for="item in report.analysis.summary.impact" :key="item">
                {{ item }}
              </li>
            </ul>
          </div>

          <div class="section-block">
            <h2>风险列表</h2>
            <div v-if="report.analysis.risks.length === 0" class="empty-state">
              暂无明确风险
            </div>
            <article
              v-for="risk in report.analysis.risks"
              v-else
              :key="`${risk.file}-${risk.line}-${risk.issue}`"
              class="risk-item"
              :class="riskClass(risk.severity)"
            >
              <div class="risk-head">
                <span class="severity-badge">{{ severityLabel[risk.severity] }}</span>
                <strong>{{ riskTitle(risk) }}</strong>
                <span>{{ toPercent(risk.confidence) }}</span>
              </div>
              <h3>{{ risk.category }}</h3>
              <p>{{ risk.issue }}</p>
              <p><b>影响：</b>{{ risk.impact }}</p>
              <p><b>建议：</b>{{ risk.suggestion }}</p>
            </article>
          </div>

          <div class="section-block">
            <h2>Review 建议</h2>
            <div v-if="report.analysis.suggestions.length === 0" class="empty-state">
              暂无建议
            </div>
            <article
              v-for="suggestion in report.analysis.suggestions"
              v-else
              :key="`${suggestion.file}-${suggestion.comment}`"
              class="suggestion-item"
              :class="suggestionClass(suggestion.type)"
            >
              <span>{{ suggestionLabel[suggestion.type] }}</span>
              <div>
                <strong>{{ suggestion.file }}</strong>
                <p>{{ suggestion.comment }}</p>
              </div>
            </article>
          </div>
        </section>
      </section>

      <section v-else class="empty-dashboard">
        <div>
          <ShieldAlert :size="30" />
          <h2>输入一个 PR 地址开始审查</h2>
          <p>系统会自动获取 GitHub 变更，调用后端 LangGraph 工作流，并生成中文结构化报告。</p>
        </div>
      </section>
    </section>
  </main>
</template>

