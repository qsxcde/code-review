<script setup lang="ts">
import { Loader2, ShieldAlert } from "lucide-vue-next";

defineProps<{
  state: "loading" | "empty";
}>();
</script>

<template>
  <section v-if="state === 'loading'" class="loading-panel">
    <Loader2 class="spin" :size="26" />
    <div>
      <h2>正在生成审查报告</h2>
      <p>正在获取 PR 变更、构建上下文并调用模型。</p>
    </div>
  </section>

  <section v-else class="empty-dashboard">
    <div>
      <ShieldAlert :size="30" />
      <h2>输入一个 PR 地址开始审查</h2>
      <p>系统会自动获取 GitHub 变更，调用后端 LangGraph 工作流，并生成中文结构化报告。</p>
    </div>
  </section>
</template>
