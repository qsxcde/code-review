<script setup lang="ts">
import { computed, ref } from "vue";
import { Files } from "@element-plus/icons-vue";
import type { PullRequestInfo } from "../types/review";

const props = defineProps<{
  pullRequest: PullRequestInfo;
  languages: string[];
}>();

const langMap: Record<string, string> = {
  py: "Python",
  ts: "TypeScript",
  js: "JavaScript",
  java: "Java",
  go: "Go",
  sql: "SQL",
};

const detailVisible = ref(false);

const escapeHtml = (value: string) =>
  value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");

const renderInlineMarkdown = (value: string) =>
  escapeHtml(value)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');

const renderedDescription = computed(() => {
  const markdown = props.pullRequest.description?.trim() || "暂无 PR 描述";
  const lines = markdown.split(/\r?\n/);
  const html: string[] = [];
  let listOpen = false;
  let codeOpen = false;

  const closeList = () => {
    if (!listOpen) return;
    html.push("</ul>");
    listOpen = false;
  };

  for (const line of lines) {
    const trimmed = line.trim();

    if (trimmed.startsWith("```")) {
      closeList();
      html.push(codeOpen ? "</code></pre>" : "<pre><code>");
      codeOpen = !codeOpen;
      continue;
    }

    if (codeOpen) {
      html.push(`${escapeHtml(line)}\n`);
      continue;
    }

    if (!trimmed) {
      closeList();
      continue;
    }

    const heading = /^(#{1,3})\s+(.+)$/.exec(trimmed);
    if (heading) {
      closeList();
      const level = heading[1].length;
      html.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
      continue;
    }

    if (/^[-*]\s+/.test(trimmed)) {
      if (!listOpen) {
        html.push("<ul>");
        listOpen = true;
      }
      html.push(`<li>${renderInlineMarkdown(trimmed.slice(2))}</li>`);
      continue;
    }

    closeList();
    html.push(`<p>${renderInlineMarkdown(trimmed)}</p>`);
  }

  closeList();
  if (codeOpen) html.push("</code></pre>");
  return html.join("");
});
</script>

<template>
  <el-card class="panel pr-info-card" shadow="never">
    <div class="pr-info-top">
      <div class="pr-copy">
        <div class="repo-line">
          <el-icon><Files /></el-icon>
          <strong>{{ pullRequest.repository }}</strong>
          <el-tag class="repo-tag" size="small">{{ pullRequest.visibility }}</el-tag>
          <span class="language-tags">
            <el-tag v-for="lang in props.languages.slice(0, 3)" :key="lang" size="small" type="info">
              {{ langMap[lang] || lang }}
            </el-tag>
            <el-tag v-if="props.languages.length > 3" size="small" type="info">
              +{{ props.languages.length - 3 }}
            </el-tag>
          </span>
        </div>
        <h2>{{ pullRequest.title }}</h2>
        <button class="description-summary" type="button" :title="pullRequest.description" @click="detailVisible = true">
          {{ pullRequest.description || "暂无 PR 描述" }}
        </button>
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

  <el-dialog
    v-model="detailVisible"
    class="pr-description-dialog"
    title="PR 详情介绍"
    width="min(760px, 92vw)"
    append-to-body
  >
    <article class="description-detail" v-html="renderedDescription" />
  </el-dialog>
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

  .description-summary {
    display: block;
    overflow: hidden;
    width: 100%;
    height: 20px;
    padding: 0;
    border: 0;
    color: $muted;
    font-size: 12px;
    line-height: 20px;
    text-align: left;
    text-overflow: ellipsis;
    white-space: nowrap;
    background: transparent;
    cursor: pointer;
  }
}

.repo-line {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  color: $text;
  font-size: 13px;
}

.language-tags {
  display: flex;
  gap: 5px;
  min-width: 0;
  overflow: hidden;
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

.description-detail {
  max-height: min(68vh, 680px);
  overflow: auto;
  color: $text;
  line-height: 1.75;

  :deep(h1),
  :deep(h2),
  :deep(h3),
  :deep(p),
  :deep(ul),
  :deep(pre) {
    margin: 0;
  }

  :deep(h1) {
    margin-bottom: 16px;
    font-size: 22px;
    font-weight: 900;
  }

  :deep(h2) {
    margin-top: 18px;
    margin-bottom: 10px;
    font-size: 18px;
    font-weight: 900;
  }

  :deep(h3) {
    margin-top: 14px;
    margin-bottom: 8px;
    font-size: 15px;
    font-weight: 800;
  }

  :deep(p) {
    margin-bottom: 10px;
    color: $muted;
    font-size: 14px;
  }

  :deep(ul) {
    display: grid;
    gap: 6px;
    margin-bottom: 12px;
    padding-left: 20px;
    color: $muted;
    font-size: 14px;
  }

  :deep(code) {
    border-radius: 4px;
    padding: 1px 5px;
    color: $text;
    background: #f1f5f9;
  }

  :deep(pre) {
    overflow: auto;
    margin-bottom: 12px;
    padding: 12px;
    border-radius: 8px;
    background: #f8fafc;
  }

  :deep(a) {
    color: $primary;
    text-decoration: none;
  }
}
</style>
