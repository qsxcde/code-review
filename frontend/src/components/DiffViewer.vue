<script setup lang="ts">
import { ref } from "vue";
import { Menu, MagicStick, Operation, ArrowRight } from "@element-plus/icons-vue";
import type { ChangedFile, AiSuggestion, CodeLine } from "../types/review";

defineProps<{
  codeLines: CodeLine[];
  changedFiles: ChangedFile[];
  aiSuggestions: AiSuggestion[];
  selectedFilePath: string;
}>();

const emit = defineEmits<{
  "select-file": [path: string];
}>();

const detailVisible = ref(false);
const detailSuggestion = ref<AiSuggestion | null>(null);

const openSuggestionDetail = (suggestion: AiSuggestion) => {
  detailSuggestion.value = suggestion;
  detailVisible.value = true;
};
</script>

<template>
  <el-card class="panel diff-card" shadow="never">
    <header class="diff-toolbar">
      <div>
        <h3>代码变更</h3>
        <span>{{ selectedFilePath || "暂无选中文件" }}</span>
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
          :key="file.path"
          class="file-item"
          :class="{ active: file.path === selectedFilePath }"
          type="button"
          @click="emit('select-file', file.path)"
        >
          <span>{{ file.path }}</span>
          <em>{{ file.alerts }}</em>
        </button>
      </aside>

      <section class="code-diff">
        <p v-if="codeLines.length === 0" class="empty-diff">选择左侧文件查看代码变更</p>
        <div v-for="line in codeLines" :key="`${line.line}-${line.code}`" class="code-line" :class="line.mark === '+' ? 'add' : line.mark === '-' ? 'remove' : ''">
          <span>{{ line.line }}</span>
          <code>{{ line.mark }} {{ line.code }}</code>
        </div>
      </section>

      <aside class="ai-suggestion">
        <h4>AI 建议</h4>
        <p v-if="aiSuggestions.length === 0" class="empty-suggestion">暂无 AI 建议</p>
        <article v-for="(suggestion, index) in aiSuggestions" :key="`${suggestion.line}-${suggestion.title}-${index}`">
          <div class="suggestion-head">
            <el-tag
              :type="suggestion.level === '高风险' ? 'danger' : suggestion.level === '中风险' ? 'warning' : 'success'"
              size="small"
            >
              {{ suggestion.level }}
            </el-tag>
            <span>{{ suggestion.line }}</span>
          </div>
          <strong>{{ suggestion.title }}</strong>
          <p class="suggestion-preview">{{ suggestion.description }}</p>
          <el-button size="small" text @click="openSuggestionDetail(suggestion)">
            查看详情 <el-icon><ArrowRight /></el-icon>
          </el-button>
        </article>
      </aside>
    </div>
  </el-card>

  <el-dialog
    v-model="detailVisible"
    class="suggestion-dialog"
    title="AI 建议详情"
    width="min(640px, 92vw)"
    append-to-body
  >
    <section v-if="detailSuggestion" class="suggestion-detail">
      <div class="suggestion-detail-head">
        <el-tag
          :type="detailSuggestion.level === '高风险' ? 'danger' : detailSuggestion.level === '中风险' ? 'warning' : 'success'"
          size="small"
        >
          {{ detailSuggestion.level }}
        </el-tag>
        <span>{{ detailSuggestion.line }}</span>
      </div>
      <h3>{{ detailSuggestion.title }}</h3>
      <p>{{ detailSuggestion.description }}</p>
    </section>
  </el-dialog>
</template>

<style scoped lang="scss">
@use "../styles/variables" as *;

.panel {
  border: 1px solid $border;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(30, 41, 59, 0.04);
  height: 100%;
  min-height: 0;
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
  height: 100%;
  min-height: 0;
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
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.file-list {
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
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
  overflow: auto;
  padding: 10px 0;
  background: #fff;
}

.empty-diff,
.empty-suggestion {
  margin: 0;
  padding: 12px 14px;
  color: $soft;
  font-size: 12px;
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
  min-width: 0;
  overflow-x: hidden;
  overflow-y: auto;
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
    min-width: 0;
    color: $text;
    font-size: 13px;
    overflow-wrap: anywhere;
  }

  p {
    margin: 0;
    color: $muted;
    font-size: 12px;
    line-height: 1.6;
    overflow-wrap: anywhere;
  }
}

.suggestion-preview {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.suggestion-head {
  display: flex;
  min-width: 0;
  justify-content: space-between;
  gap: 8px;
  color: $soft;
  font-size: 12px;

  span {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.suggestion-detail {
  display: grid;
  gap: 14px;

  h3,
  p {
    margin: 0;
  }

  h3 {
    color: $text;
    font-size: 18px;
    font-weight: 900;
  }

  p {
    color: $muted;
    font-size: 14px;
    line-height: 1.8;
    white-space: pre-wrap;
  }
}

.suggestion-detail-head {
  display: flex;
  align-items: center;
  gap: 10px;
  color: $soft;
  font-size: 12px;
}
</style>
