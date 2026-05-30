<script setup lang="ts">
import { computed } from "vue";
import { WarningFilled } from "@element-plus/icons-vue";
import type { RiskFile, RiskStats } from "../types/review";

const props = defineProps<{
  riskFiles: RiskFile[];
  riskStats: RiskStats;
  selectedRiskPath: string;
}>();

const selectedRiskFile = computed(() =>
  props.riskFiles.find((file) => file.path === props.selectedRiskPath),
);

const donutStyle = computed(() => {
  if (props.riskStats.total <= 0) {
    return {
      background:
        "radial-gradient(circle, #fff 0 52%, transparent 53%), conic-gradient(#e5e7eb 0 100%)",
    };
  }

  const high = (props.riskStats.high / props.riskStats.total) * 100;
  const medium = high + (props.riskStats.medium / props.riskStats.total) * 100;

  return {
    background:
      `radial-gradient(circle, #fff 0 52%, transparent 53%), ` +
      `conic-gradient(#ef4444 0 ${high}%, #f59e0b ${high}% ${medium}%, #315efb ${medium}% 100%)`,
  };
});
</script>

<template>
  <el-card class="panel risk-card" shadow="never">
    <h3>风险代码识别</h3>
    <div class="risk-focus">
      <el-icon><WarningFilled /></el-icon>
      <span>
        当前关注：{{ selectedRiskFile?.path || selectedRiskPath || "暂无高风险文件" }}，{{ selectedRiskFile?.count || 0 }} 个风险点
      </span>
    </div>
    <div class="donut" :style="donutStyle">
      <strong>{{ riskStats.total }}</strong>
      <span>总风险问题</span>
    </div>
    <div class="risk-legend">
      <span><i class="high" />高风险 {{ riskStats.high }}</span>
      <span><i class="medium" />中风险 {{ riskStats.medium }}</span>
      <span><i class="low" />低风险 {{ riskStats.low }}</span>
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
  overflow: hidden;

  :deep(.el-card__body) {
    height: 100%;
    padding: 16px;
    overflow: hidden;
  }
}

h3 {
  margin: 0;
  color: $text;
}

h3 { font-size: 15px; font-weight: 800; }

.risk-card :deep(.el-card__body) {
  display: grid;
  grid-template-rows: auto auto auto auto;
  align-content: start;
  gap: 14px;
}

.risk-focus {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
  padding: 9px 10px;
  border: 1px solid #fee2e2;
  border-radius: 9px;
  color: $danger;
  font-size: 12px;
  background: #fff7f7;

  span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.donut {
  display: grid;
  width: 142px;
  height: 142px;
  place-items: center;
  justify-self: center;
  border-radius: 50%;
  background:
    radial-gradient(circle, #fff 0 52%, transparent 53%),
    conic-gradient($danger 0 26%, $warning 26% 68%, $primary 68% 100%);

  strong {
    margin-top: 22px;
    color: $text;
    font-size: 24px;
    font-weight: 900;
  }

  span {
    margin-top: -36px;
    color: $soft;
    font-size: 11px;
  }
}

.risk-legend {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  color: $muted;
  font-size: 11px;

  span {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  i {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .high { background: $danger; }
  .medium { background: $warning; }
  .low { background: $primary; }
}
</style>
