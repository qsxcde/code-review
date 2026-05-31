<script setup lang="ts">
import { computed } from "vue";
import { CircleCheck, CircleClose, Loading, Minus } from "@element-plus/icons-vue";
import type { AgentStatus, ProgressState } from "../types/review";

const props = defineProps<{
  progressState: ProgressState;
}>();

const agentNames = ["[安全]", "[性能]", "[风格]"];

const statusText: Record<AgentStatus, string> = {
  idle: "等待中",
  running: "审查中",
  done: "已完成",
  error: "失败",
  skipped: "已跳过",
};

const statusIcon = (status: AgentStatus) => {
  if (status === "done") return CircleCheck;
  if (status === "error") return CircleClose;
  if (status === "running") return Loading;
  return Minus;
};

const percent = computed(() => Math.max(0, Math.min(100, props.progressState.percent)));
</script>

<template>
  <el-card class="analysis-progress" shadow="never">
    <section class="progress-main">
      <header>
        <strong>{{ progressState.reconnecting ? "重新连接中..." : progressState.currentPhase || "正在准备分析" }}</strong>
        <span>{{ percent }}%</span>
      </header>
      <el-progress :percentage="percent" :stroke-width="10" :show-text="false" />
    </section>
    <div class="agent-grid">
      <article
        v-for="agent in agentNames"
        :key="agent"
        :class="`status-${progressState.agents[agent] || 'idle'}`"
      >
        <div>
          <strong>{{ agent }}</strong>
          <span>{{ statusText[progressState.agents[agent] || "idle"] }}</span>
        </div>
        <small v-if="progressState.agentRisks[agent]">
          {{ progressState.agentRisks[agent].risks }} 风险 / {{ progressState.agentRisks[agent].high }} 高危
        </small>
        <el-icon :class="{ spinning: progressState.agents[agent] === 'running' }">
          <component :is="statusIcon(progressState.agents[agent] || 'idle')" />
        </el-icon>
      </article>
    </div>
  </el-card>
</template>

<style scoped lang="scss">
@use "../styles/variables" as *;

.analysis-progress {
  overflow: hidden;
  border: 1px solid $border;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(30, 41, 59, 0.04);

  :deep(.el-card__body) {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(360px, 1fr);
    gap: 18px;
    align-items: center;
    padding: 16px;
  }
}

.progress-main {
  display: grid;
  gap: 12px;
  min-width: 0;

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    color: $text;
    font-size: 14px;
    line-height: 1.25;

    strong {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    span {
      flex: 0 0 auto;
      color: $primary;
      font-weight: 900;
    }
  }
}

.agent-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  min-width: 0;

  article {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 6px;
    align-items: center;
    min-height: 54px;
    padding: 8px 10px;
    border: 1px solid $line;
    border-radius: 8px;
    background: #fbfdff;
    overflow: hidden;

    div {
      display: grid;
      gap: 2px;
      min-width: 0;
    }

    strong {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: $text;
      font-size: 13px;
    }

    span,
    small {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: $soft;
      font-size: 11px;
    }

    .el-icon {
      flex: 0 0 auto;
    }
  }
}

.status-running { border-color: #bfdbfe; background: #eff6ff; color: $primary; }
.status-done { border-color: #bbf7d0; background: #ecfdf3; color: $success; }
.status-error { border-color: #fecaca; background: #fff7f7; color: $danger; }
.status-skipped { border-color: #e5e7eb; background: #f8fafc; color: $soft; }

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 900px) {
  .analysis-progress :deep(.el-card__body) {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .agent-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
