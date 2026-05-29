<script setup lang="ts">
import { Menu, MagicStick, Operation, ArrowRight } from "@element-plus/icons-vue";
import type { ChangedFile, AiSuggestion } from "../types/review";

defineProps<{
  codeLines: Array<{ line: number; mark: string; code: string }>;
  changedFiles: ChangedFile[];
  aiSuggestions: AiSuggestion[];
}>();
</script>

<template>
  <el-card class="panel diff-card" shadow="never">
    <header class="diff-toolbar">
      <div>
        <h3>代码变更</h3>
        <span>service/payment_service.py</span>
      </div>
      <div class="toolbar-actions">
        <el-button size="small" :icon="Menu">统一视图</el-button>
        <el-button size="small" :icon="MagicStick">AI 标注</el-button>
        <el-button size="small" :icon="Operation" />
      </div>
    </header>

    <div class="diff-layout">
      <aside class="file-list">
        <button
          v-for="file in changedFiles"
          :key="`${file.folder}/${file.name}`"
          class="file-item"
          :class="{ active: file.active }"
        >
          <span>{{ file.folder }}/{{ file.name }}</span>
          <em>{{ file.alerts }}</em>
        </button>
      </aside>

      <section class="code-diff">
        <div v-for="line in codeLines" :key="`${line.line}-${line.code}`" class="code-line" :class="line.mark === '+' ? 'add' : line.mark === '-' ? 'remove' : ''">
          <span>{{ line.line }}</span>
          <code>{{ line.mark }} {{ line.code }}</code>
        </div>
      </section>

      <aside class="ai-suggestion">
        <h4>AI 建议</h4>
        <article v-for="suggestion in aiSuggestions" :key="suggestion.title">
          <div class="suggestion-head">
            <el-tag :type="suggestion.level === '高风险' ? 'danger' : 'warning'" size="small">{{ suggestion.level }}</el-tag>
            <span>{{ suggestion.line }}</span>
          </div>
          <strong>{{ suggestion.title }}</strong>
          <p>{{ suggestion.description }}</p>
          <el-button size="small" text>查看详情 <el-icon><ArrowRight /></el-icon></el-button>
        </article>
      </aside>
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

.diff-card :deep(.el-card__body) {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  padding: 0;
}

.diff-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  border-bottom: 1px solid $line;

  span {
    display: inline-block;
    margin-top: 4px;
    color: $muted;
    font-size: 12px;
  }
}

.toolbar-actions {
  display: flex;
  gap: 8px;
}

.diff-layout {
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr) 268px;
  min-height: 0;
}

.file-list {
  overflow: hidden;
  border-right: 1px solid $line;
  background: #fbfdff;
}

.file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  min-height: 39px;
  padding: 0 14px;
  border: 0;
  color: $muted;
  font-size: 12px;
  text-align: left;
  background: transparent;

  &.active {
    color: $primary;
    background: #eef4ff;
  }

  span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  em {
    color: $danger;
    font-style: normal;
    font-weight: 800;
  }
}

.code-diff {
  overflow: hidden;
  padding: 10px 0;
  background: #fff;
}

.code-line {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr);
  min-height: 26px;
  align-items: center;
  color: #475569;
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 12px;

  span {
    padding-right: 14px;
    color: $soft;
    text-align: right;
  }

  code {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &.add { background: #ecfdf3; }
  &.remove { background: #fff1f2; }
}

.ai-suggestion {
  overflow: hidden;
  padding: 14px;
  border-left: 1px solid $line;
  background: #fbfdff;

  article {
    display: grid;
    gap: 8px;
    padding: 12px 0;
    border-bottom: 1px solid $line;
  }

  strong {
    color: $text;
    font-size: 13px;
  }

  p {
    margin: 0;
    color: $muted;
    font-size: 12px;
    line-height: 1.6;
  }
}

.suggestion-head {
  display: flex;
  justify-content: space-between;
  color: $soft;
  font-size: 12px;
}
</style>
