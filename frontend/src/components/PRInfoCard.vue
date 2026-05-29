<script setup lang="ts">
import { Files } from "@element-plus/icons-vue";
import type { PullRequestInfo } from "../types/review";

defineProps<{
  pullRequest: PullRequestInfo;
}>();
</script>

<template>
  <el-card class="panel pr-info-card" shadow="never">
    <div class="pr-info-top">
      <div class="pr-copy">
        <div class="repo-line">
          <el-icon><Files /></el-icon>
          <strong>{{ pullRequest.repository }}</strong>
          <el-tag class="repo-tag" size="small">{{ pullRequest.visibility }}</el-tag>
        </div>
        <h2>{{ pullRequest.title }}</h2>
        <div class="description-marquee" :title="pullRequest.description">
          <span>{{ pullRequest.description }}</span>
          <span aria-hidden="true">{{ pullRequest.description }}</span>
        </div>
      </div>
      <div class="stat-grid">
        <article>
          <strong>{{ pullRequest.changedFiles }}</strong>
          <span>变更文件</span>
        </article>
        <article>
          <strong class="addition">+{{ pullRequest.additions }}</strong>
          <span>新增行数</span>
        </article>
        <article>
          <strong class="deletion">-{{ pullRequest.deletions }}</strong>
          <span>删除行数</span>
        </article>
      </div>
    </div>
    <div class="meta-grid">
      <span><em>作者</em>{{ pullRequest.author }}</span>
      <span><em>源分支</em><code>{{ pullRequest.sourceBranch }}</code></span>
      <span><em>目标分支</em><code>{{ pullRequest.targetBranch }}</code></span>
      <span><em>创建时间</em>{{ pullRequest.createdAt }}</span>
      <span><em>更新时间</em>{{ pullRequest.updatedAt }}</span>
      <span><em>状态</em><el-tag class="open-tag" size="small">{{ pullRequest.state }}</el-tag></span>
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

  :deep(.el-card__body) {
    height: 100%;
    padding: 16px;
  }
}

.pr-info-card :deep(.el-card__body) {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 8px;
  padding: 12px 16px 14px;
}

.pr-info-top {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 386px;
  gap: 20px;
  align-items: center;
}

.pr-copy {
  min-width: 0;
  padding-top: 2px;

  h2 {
    overflow: hidden;
    margin: 8px 0 4px;
    color: $text;
    font-size: 16px;
    font-weight: 800;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .description-marquee {
    position: relative;
    overflow: hidden;
    max-width: 100%;
    height: 20px;
    margin: 0;
    color: $muted;
    font-size: 12px;
    line-height: 20px;
    white-space: nowrap;

    span {
      display: inline-block;
      min-width: 100%;
      padding-right: 48px;
      animation: pr-description-marquee 14s linear infinite;
    }

    &:hover span {
      animation-play-state: paused;
    }
  }
}

@keyframes pr-description-marquee {
  0% { transform: translateX(0); }
  45% { transform: translateX(0); }
  100% { transform: translateX(-100%); }
}

.repo-line {
  display: flex;
  align-items: center;
  gap: 8px;
  color: $text;
  font-size: 13px;
}

.repo-tag {
  border-color: #bfdbfe;
  color: #2563eb;
  background: #eff6ff;
}

.meta-grid {
  display: grid;
  grid-template-columns: 0.72fr 1.45fr 1fr 1.3fr 1.3fr 0.7fr;
  gap: 10px;
  width: 100%;
  padding-top: 9px;
  border-top: 1px solid $line;

  span {
    display: grid;
    gap: 6px;
    min-width: 0;
    color: $text;
    font-size: 12px;
  }

  em {
    color: $soft;
    font-size: 11px;
    font-style: normal;
  }

  code {
    overflow: hidden;
    font-family: "SFMono-Regular", Consolas, monospace;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.open-tag {
  width: fit-content;
  border-color: #bbf7d0;
  color: $success;
  background: #ecfdf3;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  align-items: center;
  align-self: center;
  transform: translateY(4px);

  article {
    display: grid;
    min-height: 62px;
    place-items: center;
    align-content: center;
    gap: 5px;
    border: 1px solid $line;
    border-radius: 10px;
    background: #fbfdff;
  }

  strong {
    color: $text;
    font-size: 18px;
    font-weight: 800;
  }

  span {
    color: $muted;
    font-size: 10px;
  }

  .addition { color: $success; }
  .deletion { color: $danger; }
}
</style>
