import type { DataAnalysis } from "@element-plus/icons-vue";

export type ActiveView = "analysis" | "history" | "reports" | "settings";

export interface NavItem {
  key: ActiveView;
  label: string;
  icon: typeof DataAnalysis;
  active?: boolean;
}
