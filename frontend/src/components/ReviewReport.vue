<script setup lang="ts">
import { Clipboard, ExternalLink, FileText, ShieldAlert } from "lucide-vue-next";
import type { ReviewAnalyzeResponse } from "../types/review";
import {
  formatMs,
  riskClass,
  riskTitle,
  severityLabel,
  suggestionClass,
  suggestionLabel,
  toPercent,
} from "../utils/reviewFormat";

defineProps<{
  report: ReviewAnalyzeResponse;
  copied: boolean;
}>();

const emit = defineEmits<{
  copy: [];
}>();
</script>

<template>
  <section class="report-layout">
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
          <span>入模文件</span>
        </div>
      </div>

      <button class="secondary-button" type="button" @click="emit('copy')">
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

      <div v-if="report.analysis.warnings.length" class="section-block">
        <h2>审计提示</h2>
        <ul class="warning-list">
          <li v-for="warning in report.analysis.warnings" :key="warning">
            {{ warning }}
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
</template>
