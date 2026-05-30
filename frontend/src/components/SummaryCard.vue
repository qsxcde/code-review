<script setup lang="ts">
import type { SummaryItem } from "../types/review";

defineProps<{
  summaryItems: SummaryItem[];
  summaryTags: string[];
  activeSummaryTag: string;
}>();

const emit = defineEmits<{
  filter: [tag: string];
}>();
</script>

<template>
  <el-card class="panel summary-card" shadow="never">
    <header class="summary-head">
      <h3>PR 变更总结</h3>
    </header>
    <div class="summary-filter" aria-label="变更总结筛选">
      <button
        v-for="tag in summaryTags"
        :key="tag"
        type="button"
        :class="{ active: activeSummaryTag === tag }"
        @click="emit('filter', tag)"
      >
        {{ tag }}
      </button>
    </div>
    <ul class="summary-list">
      <li v-for="item in summaryItems" :key="item.text">
        <span>{{ item.text }}</span>
        <el-tag :class="`tag-${item.tone}`" size="small">{{ item.tag }}</el-tag>
      </li>
      <li v-if="summaryItems.length === 0" class="empty-row">
        <span>暂无该类型的变更总结</span>
      </li>
    </ul>
  </el-card>
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

  :deep(.el-card__body) {
    display: grid;
    grid-template-rows: auto auto minmax(0, 1fr);
    gap: 16px;
    height: 100%;
    padding: 16px;
    min-height: 0;
  }
}

h3 {
  margin: 0;
  color: $text;
  font-size: 15px;
  font-weight: 800;
}

.summary-head {
  min-height: 22px;
}

.summary-list {
  display: grid;
  align-content: start;
  gap: 14px;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 0;
  margin: 0;
  padding-right: 4px;
  list-style: none;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-thumb {
    border-radius: 999px;
    background: #dbe3ef;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }
}

.summary-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-content: start;
  max-height: 78px;
  overflow: hidden;

  button {
    height: 30px;
    padding: 0 14px;
    border: 1px solid $line;
    border-radius: 999px;
    color: $muted;
    font-size: 13px;
    font-weight: 700;
    background: #fbfdff;
    cursor: pointer;

    &.active {
      border-color: #c7d2fe;
      color: $primary;
      background: #eef4ff;
    }
  }
}

.summary-card li {
  display: grid;
  grid-template-columns: minmax(0, 1fr) max-content;
  gap: 12px;
  align-items: center;
  color: $muted;
  font-size: 14px;
  line-height: 1.55;

  span:first-child {
    min-width: 0;
    word-break: break-word;
  }
}

.empty-row {
  color: $soft;
}

.tag-green { color: $success; background: #ecfdf3; }
.tag-blue { color: $primary; background: #eef4ff; }
.tag-orange { color: $warning; background: #fffbeb; }
.tag-violet { color: #7c3aed; background: #f5f3ff; }
</style>
