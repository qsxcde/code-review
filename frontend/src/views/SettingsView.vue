<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Delete, Edit, Plus, Refresh, Search } from "@element-plus/icons-vue";
import {
  ruleCategoryLabel,
  ruleCategoryOptions,
  ruleCategoryTagType,
  useReviewRules,
} from "../composables/useReviewRules";
import type { ReviewRule, ReviewRuleCategory, ReviewRulePayload } from "../types/reviewRule";

const props = defineProps<{
  apiBaseUrl: string;
  accessToken: string;
}>();

const emit = defineEmits<{
  "require-login": [];
}>();

const {
  rules,
  total,
  loading,
  saving,
  categoryFilter,
  loadRules,
  saveRule,
  patchRule,
  removeRule,
} = useReviewRules(
  () => props.apiBaseUrl,
  () => props.accessToken,
  () => emit("require-login"),
);

interface RuleFormState {
  name: string;
  description: string;
  category: ReviewRuleCategory;
  prompt_content: string;
  includeText: string;
  excludeText: string;
  priority: number;
}

const dialogVisible = ref(false);
const editingRule = ref<ReviewRule | null>(null);
const form = reactive<RuleFormState>({
  name: "",
  description: "",
  category: "custom",
  prompt_content: "",
  includeText: "",
  excludeText: "",
  priority: 0,
});

const splitFilters = (value: string) =>
  value
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);

const categoryLabel = (category: ReviewRuleCategory) => ruleCategoryLabel[category];

const resetForm = () => {
  editingRule.value = null;
  form.name = "";
  form.description = "";
  form.category = "custom";
  form.prompt_content = "";
  form.includeText = "";
  form.excludeText = "";
  form.priority = 0;
};

const openCreateDialog = () => {
  resetForm();
  dialogVisible.value = true;
};

const openEditDialog = (rule: ReviewRule) => {
  editingRule.value = rule;
  form.name = rule.name;
  form.description = rule.description || "";
  form.category = rule.category;
  form.prompt_content = rule.prompt_content;
  form.includeText = rule.file_filters?.include.join("\n") || "";
  form.excludeText = rule.file_filters?.exclude.join("\n") || "";
  form.priority = rule.priority;
  dialogVisible.value = true;
};

const buildPayload = (): ReviewRulePayload => {
  const include = splitFilters(form.includeText);
  const exclude = splitFilters(form.excludeText);

  return {
    name: form.name.trim(),
    description: form.description.trim() || null,
    category: form.category,
    prompt_content: form.prompt_content.trim(),
    file_filters: include.length || exclude.length ? { include, exclude } : null,
    priority: form.priority,
  };
};

const submitRule = async () => {
  if (!form.name.trim() || !form.prompt_content.trim()) {
    ElMessage.warning("请填写规则名称和规则内容");
    return;
  }

  const saved = await saveRule(buildPayload(), editingRule.value);
  if (saved) {
    dialogVisible.value = false;
  }
};

const toggleRule = (rule: ReviewRule, enabled: boolean | string | number) => {
  void patchRule(rule, { is_enabled: Boolean(enabled) });
};

const deleteRule = (rule: ReviewRule) => {
  void removeRule(rule).catch(() => undefined);
};

onMounted(() => {
  void loadRules();
});
</script>

<template>
  <section class="settings-view">
    <header class="settings-head">
      <div>
        <h2>自定义审查规则</h2>
        <p>配置团队专属审查策略，分析时会自动注入对应专家 Agent。</p>
      </div>
      <el-button class="primary-button" type="primary" :icon="Plus" @click="openCreateDialog">
        新建规则
      </el-button>
    </header>

    <div class="settings-toolbar">
      <el-select v-model="categoryFilter" class="category-filter" @change="loadRules">
        <el-option
          v-for="option in ruleCategoryOptions"
          :key="option.value || 'all'"
          :label="option.label"
          :value="option.value"
        />
      </el-select>
      <el-button :icon="Search" @click="loadRules">筛选</el-button>
      <el-button :icon="Refresh" :loading="loading" @click="loadRules">刷新</el-button>
      <span>{{ total }} 条规则</span>
    </div>

    <div class="rules-table-wrap">
      <el-table v-loading="loading" :data="rules" height="100%" row-key="id">
        <el-table-column label="规则" min-width="280">
          <template #default="{ row }">
            <div class="rule-name-cell">
              <strong>{{ row.name }}</strong>
              <span>{{ row.description || "暂无描述" }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="类别" width="100">
          <template #default="{ row }">
            <el-tag :type="ruleCategoryTagType(row.category)" size="small">
              {{ categoryLabel(row.category) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="90" />
        <el-table-column label="启用" width="90">
          <template #default="{ row }">
            <el-switch :model-value="row.is_enabled" @change="toggleRule(row, $event)" />
          </template>
        </el-table-column>
        <el-table-column label="文件过滤" min-width="190">
          <template #default="{ row }">
            <div class="filter-cell">
              <span>包含 {{ row.file_filters?.include?.length || 0 }}</span>
              <span>排除 {{ row.file_filters?.exclude?.length || 0 }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button :icon="Edit" size="small" text @click="openEditDialog(row)">编辑</el-button>
            <el-button :icon="Delete" size="small" text type="danger" @click="deleteRule(row)" />
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="editingRule ? '编辑审查规则' : '新建审查规则'"
      width="min(760px, 92vw)"
      append-to-body
    >
      <el-form class="rule-form" label-position="top">
        <div class="rule-form-grid">
          <el-form-item label="规则名称" required>
            <el-input v-model="form.name" maxlength="128" show-word-limit />
          </el-form-item>
          <el-form-item label="类别">
            <el-select v-model="form.category">
              <el-option
                v-for="option in ruleCategoryOptions.filter((item) => item.value)"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="优先级">
            <el-input-number v-model="form.priority" :min="0" :max="100" controls-position="right" />
          </el-form-item>
        </div>
        <el-form-item label="描述">
          <el-input v-model="form.description" maxlength="512" show-word-limit />
        </el-form-item>
        <el-form-item label="规则内容" required>
          <el-input
            v-model="form.prompt_content"
            type="textarea"
            :rows="8"
            maxlength="4096"
            show-word-limit
          />
        </el-form-item>
        <div class="filter-form-grid">
          <el-form-item label="包含文件">
            <el-input v-model="form.includeText" type="textarea" :rows="3" placeholder="每行或逗号分隔，如 src/**/*.ts" />
          </el-form-item>
          <el-form-item label="排除文件">
            <el-input v-model="form.excludeText" type="textarea" :rows="3" placeholder="每行或逗号分隔，如 tests/**" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button class="primary-button" type="primary" :loading="saving" @click="submitRule">
            保存规则
          </el-button>
        </div>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped lang="scss">
@use "../styles/variables" as *;

.settings-view {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  gap: 14px;
  height: 100%;
  min-height: 0;
}

.settings-head,
.settings-toolbar,
.rules-table-wrap {
  border: 1px solid $border;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 10px 28px rgba(30, 41, 59, 0.04);
}

.settings-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;

  h2,
  p {
    margin: 0;
  }

  h2 {
    color: $text;
    font-size: 20px;
    font-weight: 900;
  }

  p {
    margin-top: 6px;
    color: $muted;
    font-size: 13px;
  }
}

.settings-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px;

  span {
    margin-left: auto;
    color: $soft;
    font-size: 12px;
  }
}

.category-filter {
  width: 150px;
}

.rules-table-wrap {
  min-height: 0;
  overflow: hidden;
}

.rule-name-cell {
  display: grid;
  gap: 4px;
  min-width: 0;

  strong,
  span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  strong {
    color: $text;
    font-size: 13px;
  }

  span {
    color: $soft;
    font-size: 12px;
  }
}

.filter-cell {
  display: flex;
  gap: 8px;
  color: $muted;
  font-size: 12px;
}

.rule-form {
  display: grid;
  gap: 4px;
}

.rule-form-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 150px 120px;
  gap: 12px;
}

.filter-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.primary-button {
  border: 0;
  border-radius: 8px;
  font-weight: 800;
  background: $primary-gradient;
}

@media (max-width: 900px) {
  .settings-head,
  .settings-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .settings-toolbar span {
    margin-left: 0;
  }

  .category-filter {
    width: 100%;
  }

  .rule-form-grid,
  .filter-form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
