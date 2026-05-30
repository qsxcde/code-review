import type { DataAnalysis } from "@element-plus/icons-vue";

export interface InsightCard {
  title: string;
  icon: typeof DataAnalysis;
  rows: string[];
}
