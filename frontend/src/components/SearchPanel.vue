<script setup lang="ts">
import { Link } from "@element-plus/icons-vue";

defineProps<{
  prUrl: string;
  isAnalyzing: boolean;
  analysisStatus: "idle" | "analyzing" | "completed" | "failed";
  analysisStatusText: string;
  analysisDuration: number;
  analyzedUrl: string;
  backendWarning: string;
}>();

const emit = defineEmits<{
  analyze: [];
  "update:prUrl": [value: string];
}>();
</script>

<template>
  <el-card class="panel search-card" shadow="never">
    <h2>指定 GitHub PR</h2>
    <el-input
      :model-value="prUrl"
      class="pr-input"
      :prefix-icon="Link"
      :disabled="isAnalyzing"
      clearable
      @update:model-value="emit('update:prUrl', $event)"
      @keyup.enter="emit('analyze')"
    />
    <div class="search-actions">
      <el-button class="primary-button" type="primary" :loading="isAnalyzing" @click="emit('analyze')">
        {{ isAnalyzing ? "分析中" : "开始分析" }}
      </el-button>
    </div>
    <div class="analysis-status" :class="`status-${analysisStatus}`">
      <span class="status-dot" />
      <span>{{ analysisStatusText }}</span>
      <em v-if="analysisStatus === 'completed'">耗时：{{ analysisDuration.toFixed(1) }}s</em>
    </div>
    <p class="analyzed-url">当前 PR：{{ analyzedUrl }}</p>
    <p v-if="backendWarning" class="backend-warning">{{ backendWarning }}</p>
  </el-card>
</template>

<style scoped lang="scss">
@use "../styles/variables" as *;

.panel {
  border: 1px solid $border;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(30, 41, 59, 0.04);

  :deep(.el-card__body) {
    height: 100%;
    padding: 16px;
  }
}

.search-card {
  :deep(.el-card__body) {
    display: grid;
    align-content: center;
    gap: 10px;
    padding: 14px;
  }

  h2 {
    margin: 0;
    color: $text;
    font-size: 17px;
    font-weight: 800;
  }
}

.pr-input :deep(.el-input__wrapper) {
  min-height: 38px;
  border-radius: 8px;
  box-shadow: 0 0 0 1px #dbe3ef inset;
}

.search-actions {
  display: grid;

  .primary-button {
    width: 100%;
    min-height: 38px;
  }
}

.primary-button {
  border: 0;
  border-radius: 8px;
  font-weight: 800;
  background: $primary-gradient;
}

.analysis-status {
  display: flex;
  align-items: center;
  gap: 8px;
  color: $muted;
  font-size: 12px;

  em {
    color: $soft;
    font-style: normal;
  }

  &.status-analyzing {
    color: $primary;
  }

  &.status-failed {
    color: $danger;
  }
}

.status-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: $success;
  box-shadow: 0 0 0 4px rgba(22, 163, 74, 0.12);
}

.status-analyzing .status-dot {
  background: $primary;
  box-shadow: 0 0 0 4px rgba(49, 94, 251, 0.12);
}

.status-failed .status-dot {
  background: $danger;
  box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.12);
}

.analyzed-url {
  overflow: hidden;
  margin: -2px 0 0;
  color: $soft;
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.backend-warning {
  overflow: hidden;
  margin: -4px 0 0;
  color: $warning;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
