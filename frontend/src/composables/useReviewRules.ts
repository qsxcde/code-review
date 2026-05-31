import { ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  createReviewRule,
  deleteReviewRule,
  fetchReviewRules,
  updateReviewRule,
} from "../api/rulesApi";
import type {
  ReviewRule,
  ReviewRuleCategory,
  ReviewRulePayload,
  ReviewRuleUpdatePayload,
} from "../types/reviewRule";

export const ruleCategoryOptions: Array<{ label: string; value: ReviewRuleCategory | "" }> = [
  { label: "全部类别", value: "" },
  { label: "安全", value: "security" },
  { label: "性能", value: "performance" },
  { label: "风格", value: "style" },
  { label: "自定义", value: "custom" },
];

export const ruleCategoryLabel: Record<ReviewRuleCategory, string> = {
  security: "安全",
  performance: "性能",
  style: "风格",
  custom: "自定义",
};

export const ruleCategoryTagType = (category: ReviewRuleCategory) => {
  if (category === "security") return "danger";
  if (category === "performance") return "warning";
  if (category === "style") return "primary";
  return "info";
};

export const useReviewRules = (
  getApiBaseUrl: () => string,
  getAccessToken: () => string,
  requireLogin: () => void,
) => {
  const rules = ref<ReviewRule[]>([]);
  const total = ref(0);
  const loading = ref(false);
  const saving = ref(false);
  const categoryFilter = ref<ReviewRuleCategory | "">("");

  const ensureToken = () => {
    const token = getAccessToken();
    if (!token) {
      requireLogin();
      return "";
    }
    return token;
  };

  const loadRules = async () => {
    const token = ensureToken();
    if (!token) return;

    loading.value = true;
    try {
      const data = await fetchReviewRules(getApiBaseUrl(), token, categoryFilter.value);
      rules.value = data.items;
      total.value = data.total;
    } catch (error) {
      const message = error instanceof Error ? error.message : "规则加载失败";
      ElMessage.error(message);
    } finally {
      loading.value = false;
    }
  };

  const saveRule = async (
    payload: ReviewRulePayload,
    editingRule: ReviewRule | null,
  ) => {
    const token = ensureToken();
    if (!token) return false;

    saving.value = true;
    try {
      if (editingRule) {
        await updateReviewRule(getApiBaseUrl(), token, editingRule.id, payload);
        ElMessage.success("规则已更新");
      } else {
        await createReviewRule(getApiBaseUrl(), token, payload);
        ElMessage.success("规则已创建");
      }
      await loadRules();
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : "规则保存失败";
      ElMessage.error(message);
      return false;
    } finally {
      saving.value = false;
    }
  };

  const patchRule = async (rule: ReviewRule, payload: ReviewRuleUpdatePayload) => {
    const token = ensureToken();
    if (!token) return;

    try {
      await updateReviewRule(getApiBaseUrl(), token, rule.id, payload);
      await loadRules();
    } catch (error) {
      const message = error instanceof Error ? error.message : "规则更新失败";
      ElMessage.error(message);
    }
  };

  const removeRule = async (rule: ReviewRule) => {
    const token = ensureToken();
    if (!token) return;

    try {
      await ElMessageBox.confirm(`确认删除规则“${rule.name}”？`, "删除规则", {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
      });
    } catch {
      return;
    }

    try {
      await deleteReviewRule(getApiBaseUrl(), token, rule.id);
      rules.value = rules.value.filter((item) => item.id !== rule.id);
      total.value = Math.max(0, total.value - 1);
      ElMessage.success("规则已删除");
      await loadRules();
    } catch (error) {
      const message = error instanceof Error ? error.message : "规则删除失败";
      ElMessage.error(message);
      if (message.includes("401") || message.includes("token")) requireLogin();
    }
  };
  return {
    rules,
    total,
    loading,
    saving,
    categoryFilter,
    loadRules,
    saveRule,
    patchRule,
    removeRule,
  };
};
