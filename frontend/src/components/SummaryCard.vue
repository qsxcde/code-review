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
    <h3>PR 变更总结</h3>
    <div class="summary-filter">
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
    <ul>
      <li v-for="item in summaryItems" :key="item.text">
        <span>{{ item.text }}</span>
        <el-tag :class="`tag-${item.tone}`" size="small">{{ item.tag }}</el-tag>
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

  :deep(.el-card__body) {
    height: 100%;
    padding: 16px;
  }
}

h3 {
  margin: 0;
  color: $text;
  font-size: 15px;
  font-weight: 800;
}

.summary-card ul {
  display: grid;
  gap: 12px;
  padding: 0;
  margin: 16px 0 0;
  list-style: none;
}

.summary-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;

  button {
    height: 26px;
    padding: 0 10px;
    border: 1px solid $line;
    border-radius: 999px;
    color: $muted;
    font-size: 12px;
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
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  color: $muted;
  font-size: 12px;
  line-height: 1.45;
}

.tag-green { color: $success; background: #ecfdf3; }
.tag-blue { color: $primary; background: #eef4ff; }
.tag-orange { color: $warning; background: #fffbeb; }
.tag-violet { color: #7c3aed; background: #f5f3ff; }
</style>
