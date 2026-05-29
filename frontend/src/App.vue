<script setup lang="ts">
import { computed, onUnmounted, ref } from "vue";
import { CheckCircle2 } from "lucide-vue-next";
import { analyzePullRequest } from "./api/reviewApi";
import ReviewForm from "./components/ReviewForm.vue";
import ReviewReport from "./components/ReviewReport.vue";
import ReviewStatePanel from "./components/ReviewStatePanel.vue";
import type { ReviewAnalyzeResponse } from "./types/review";
import { toMarkdown } from "./utils/reviewFormat";

const prUrl = ref("https://github.com/fastapi/fastapi/pull/1");
const loading = ref(false);
const errorMessage = ref("");
const copied = ref(false);
const report = ref<ReviewAnalyzeResponse | null>(null);
const analysisController = ref<AbortController | null>(null);

const canSubmit = computed(() => prUrl.value.trim().length > 0 && !loading.value);

async function runAnalysis() {
  if (!canSubmit.value) return;

  const controller = new AbortController();
  analysisController.value = controller;
  loading.value = true;
  errorMessage.value = "";
  copied.value = false;

  try {
    report.value = await analyzePullRequest(prUrl.value.trim(), {
      signal: controller.signal,
    });
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "分析失败";
  } finally {
    if (analysisController.value === controller) {
      analysisController.value = null;
      loading.value = false;
    }
  }
}

function cancelAnalysis() {
  analysisController.value?.abort();
}

async function copyMarkdown() {
  if (!report.value) return;
  await navigator.clipboard.writeText(toMarkdown(report.value));
  copied.value = true;
  window.setTimeout(() => {
    copied.value = false;
  }, 1600);
}

onUnmounted(() => {
  cancelAnalysis();
});
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

      <ReviewForm
        v-model="prUrl"
        :loading="loading"
        :can-submit="canSubmit"
        :error-message="errorMessage"
        @submit="runAnalysis"
        @cancel="cancelAnalysis"
      />

      <ReviewStatePanel v-if="loading" state="loading" />
      <ReviewReport
        v-else-if="report"
        :report="report"
        :copied="copied"
        @copy="copyMarkdown"
      />
      <ReviewStatePanel v-else state="empty" />
    </section>
  </main>
</template>
