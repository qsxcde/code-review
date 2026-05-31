<script setup lang="ts">
import { onMounted } from "vue";
import { Refresh, TrendCharts, WarningFilled } from "@element-plus/icons-vue";
import { useReviewStats } from "../composables/useReviewStats";

const props = defineProps<{
  apiBaseUrl: string;
  accessToken: string;
}>();

const emit = defineEmits<{
  "require-login": [];
}>();

const { stats, loading, loadStats, agentLabel, percent } = useReviewStats(
  () => props.apiBaseUrl,
  () => props.accessToken,
  () => emit("require-login"),
);

onMounted(() => {
  void loadStats();
});
</script>

<template>
  <section class="stats-view">
    <header class="stats-head">
      <div>
        <h2>审查质量统计</h2>
        <p>基于用户反馈（有帮助 / 无用 / 误报）汇总各 Agent 的表现。</p>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadStats">刷新</el-button>
    </header>

    <div v-if="!stats" class="stats-empty">
      <p>暂无统计数据，完成审查并提交反馈后即可查看。</p>
    </div>

    <template v-else>
      <div class="stats-summary-grid">
        <article>
          <strong>{{ stats.total_analyses }}</strong>
          <span>累计审查</span>
        </article>
        <article>
          <strong>{{ stats.total_risks_flagged }}</strong>
          <span>发现风险</span>
        </article>
        <article>
          <strong>{{ percent(stats.feedback_coverage) }}</strong>
          <span>反馈覆盖率</span>
        </article>
        <article class="fp-card">
          <strong>{{ percent(stats.false_positive_rate) }}</strong>
          <span>误报率</span>
        </article>
      </div>

      <div class="agent-cards">
        <div
          v-for="agent in stats.by_agent"
          :key="agent.agent"
          class="agent-card"
        >
          <div class="agent-card-head">
            <el-tag
              :type="agent.agent === '安全' ? 'danger' : agent.agent === '性能' ? 'warning' : 'primary'"
              size="small"
            >
              {{ agentLabel(agent.agent) }}
            </el-tag>
            <span>发现 {{ agent.total_risks }} 个风险</span>
          </div>
          <div class="agent-card-bars">
            <div class="bar-row">
              <span class="bar-label helpful">有帮助</span>
              <div class="bar-track">
                <div
                  class="bar-fill helpful-fill"
                  :style="{ width: percent(agent.helpful / agent.total_risks || 0) }"
                />
              </div>
              <strong>{{ agent.helpful }}</strong>
            </div>
            <div class="bar-row">
              <span class="bar-label not-helpful">无用</span>
              <div class="bar-track">
                <div
                  class="bar-fill not-helpful-fill"
                  :style="{ width: percent(agent.not_helpful / agent.total_risks || 0) }"
                />
              </div>
              <strong>{{ agent.not_helpful }}</strong>
            </div>
            <div class="bar-row">
              <span class="bar-label false-positive">误报</span>
              <div class="bar-track">
                <div
                  class="bar-fill fp-fill"
                  :style="{ width: percent(agent.false_positive_rate) }"
                />
              </div>
              <strong>{{ percent(agent.false_positive_rate) }}</strong>
            </div>
          </div>
        </div>
      </div>

      <section v-if="stats.recent_false_positives.length" class="recent-fps">
        <h3>
          <el-icon><WarningFilled /></el-icon>
          最近误报
        </h3>
        <div v-for="fp in stats.recent_false_positives" :key="`${fp.record_id}-${fp.file}`" class="fp-item">
          <span class="fp-file">{{ fp.file }}</span>
          <span class="fp-issue">{{ fp.issue }}</span>
        </div>
      </section>
    </template>
  </section>
</template>

<style scoped lang="scss">
@use "../styles/variables" as *;

.stats-view {
  display: grid;
  grid-template-rows: auto auto auto auto;
  gap: 14px;
  height: 100%;
  overflow: auto;
  padding-bottom: 20px;
}

.stats-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  border: 1px solid $border;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(30, 41, 59, 0.04);

  h2, p { margin: 0; }
  h2 { color: $text; font-size: 20px; font-weight: 900; }
  p { margin-top: 6px; color: $muted; font-size: 13px; }
}

.stats-empty {
  display: grid;
  place-content: center;
  min-height: 260px;
  border: 1px solid $border;
  border-radius: 12px;
  background: #fff;
  color: $muted;
  font-size: 13px;
}

.stats-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;

  article {
    display: grid;
    place-content: center;
    gap: 6px;
    padding: 24px 16px;
    border: 1px solid $border;
    border-radius: 12px;
    background: #fff;
    text-align: center;
    box-shadow: 0 10px 28px rgba(30, 41, 59, 0.04);

    strong { color: $text; font-size: 28px; font-weight: 900; }
    span { color: $muted; font-size: 12px; }
  }

  .fp-card strong { color: $danger; }
}

.agent-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.agent-card {
  display: grid;
  gap: 12px;
  padding: 18px 20px;
  border: 1px solid $border;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(30, 41, 59, 0.04);
}

.agent-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;

  span { color: $soft; font-size: 12px; }
}

.agent-card-bars {
  display: grid;
  gap: 8px;
}

.bar-row {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr) 44px;
  align-items: center;
  gap: 8px;
}

.bar-label {
  color: $muted;
  font-size: 11px;
}

.bar-track {
  height: 6px;
  border-radius: 3px;
  background: #f1f5f9;
}

.bar-fill {
  height: 100%;
  border-radius: 3px;
}

.helpful-fill { background: $success; }
.not-helpful-fill { background: #f59e0b; }
.fp-fill { background: $danger; }

.bar-row strong {
  color: $text;
  font-size: 12px;
  font-weight: 800;
  text-align: right;
}

.recent-fps {
  padding: 18px 20px;
  border: 1px solid $border;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(30, 41, 59, 0.04);

  h3 {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 0 0 12px;
    color: $danger;
    font-size: 15px;
    font-weight: 800;
  }
}

.fp-item {
  display: flex;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid $line;

  &:last-child { border: 0; }

  .fp-file {
    flex-shrink: 0;
    min-width: 180px;
    color: $text;
    font-family: monospace;
    font-size: 12px;
  }

  .fp-issue {
    color: $muted;
    font-size: 12px;
  }
}

@media (max-width: 960px) {
  .stats-summary-grid { grid-template-columns: repeat(2, 1fr); }
  .agent-cards { grid-template-columns: 1fr; }
}
</style>
