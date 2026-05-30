<script setup lang="ts">
import { computed, ref } from "vue";
import { ElMessage } from "element-plus";
import {
  Clock,
  DataAnalysis,
  Document,
  Lock,
  Message,
  Setting,
} from "@element-plus/icons-vue";
import { useAuth } from "./composables/useAuth";
import type { ActiveView, NavItem } from "./types/navigation";
import AppSidebar from "./components/AppSidebar.vue";
import HistoryView from "./components/HistoryView.vue";
import AnalysisView from "./views/AnalysisView.vue";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "/api/v1";
const activeView = ref<ActiveView>("analysis");

const {
  authSession,
  authDialogVisible,
  authMode,
  authEmail,
  authPassword,
  authLoading,
  currentAccessToken,
  openAuthDialog,
  handleAuthSubmit,
  handleLogout,
  expireSession,
} = useAuth(apiBaseUrl);

const navItems = computed<NavItem[]>(() => [
  { key: "analysis", label: "PR 分析", icon: DataAnalysis, active: activeView.value === "analysis" },
  { key: "history", label: "历史分析", icon: Clock, active: activeView.value === "history" },
  { key: "reports", label: "报告中心", icon: Document, active: activeView.value === "reports" },
  { key: "settings", label: "设置中心", icon: Setting, active: activeView.value === "settings" },
]);

const requireLogin = () => {
  openAuthDialog("login");
};

const handleSelectView = (view: ActiveView) => {
  if (view === "history" && !currentAccessToken.value) {
    requireLogin();
    ElMessage.warning("请先登录后查看历史分析");
    return;
  }

  activeView.value = view;
};
</script>

<template>
  <div class="app-shell">
    <AppSidebar
      :nav-items="navItems"
      :user="authSession?.user || null"
      @select="handleSelectView"
      @login="openAuthDialog('login')"
      @register="openAuthDialog('register')"
      @logout="handleLogout"
    />

    <AnalysisView
      v-if="activeView === 'analysis'"
      :api-base-url="apiBaseUrl"
      :access-token="currentAccessToken"
      @require-login="requireLogin"
      @expire-session="expireSession"
    />

    <main v-else-if="activeView === 'history'" class="workspace">
      <HistoryView
        :api-base-url="apiBaseUrl"
        :access-token="currentAccessToken"
        @require-login="requireLogin"
      />
    </main>

    <main v-else class="workspace placeholder-workspace">
      <section class="placeholder-panel">
        <h2>{{ activeView === "reports" ? "报告中心" : "设置中心" }}</h2>
        <p>该模块稍后接入。</p>
      </section>
    </main>

    <el-dialog
      v-model="authDialogVisible"
      class="auth-dialog"
      :title="authMode === 'login' ? '登录账号' : '注册账号'"
      width="380px"
      append-to-body
    >
      <el-form label-position="top" @submit.prevent="handleAuthSubmit">
        <el-form-item label="邮箱">
          <el-input
            v-model="authEmail"
            :prefix-icon="Message"
            placeholder="name@example.com"
            autocomplete="email"
          />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="authPassword"
            :prefix-icon="Lock"
            type="password"
            show-password
            placeholder="至少 8 位，包含字母和数字"
            autocomplete="current-password"
            @keyup.enter="handleAuthSubmit"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="auth-footer">
          <el-button text @click="authMode = authMode === 'login' ? 'register' : 'login'">
            {{ authMode === "login" ? "没有账号，去注册" : "已有账号，去登录" }}
          </el-button>
          <el-button class="auth-primary" type="primary" :loading="authLoading" @click="handleAuthSubmit">
            {{ authMode === "login" ? "登录" : "注册" }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss">
@use "./styles/variables" as *;

.app-shell {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: $page;
}

.workspace {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 12px;
  min-width: 0;
  height: 100%;
  padding: 18px 18px 16px;
  overflow: hidden;
}

.hero-row {
  display: grid;
  grid-template-columns: minmax(320px, 30%) minmax(0, 70%);
  gap: 16px;
  min-height: 126px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(230px, 20%) minmax(0, 60%) minmax(260px, 20%);
  gap: 16px;
  min-height: 0;
}

.left-column,
.center-column {
  display: grid;
  gap: 16px;
  min-height: 0;
}

.left-column {
  grid-template-rows: minmax(340px, 1fr) 310px;
}

.center-column {
  grid-template-rows: minmax(0, 1fr);
}

.right-column {
  min-height: 0;
}

.placeholder-workspace {
  grid-template-rows: minmax(0, 1fr);
}

.placeholder-panel {
  display: grid;
  place-content: center;
  gap: 8px;
  min-height: 0;
  border: 1px solid $border;
  border-radius: 12px;
  color: $muted;
  background: #fff;

  h2,
  p {
    margin: 0;
    text-align: center;
  }

  h2 {
    color: $text;
    font-size: 20px;
  }
}

.auth-dialog .el-dialog__body {
  padding-top: 8px;
}

.auth-footer {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.auth-primary {
  border: 0;
  background: $primary-gradient;
}

.report-dialog .el-textarea__inner {
  font-family: "SFMono-Regular", Consolas, monospace;
  line-height: 1.6;
}

.report-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 1440px) {
  .app-shell {
    grid-template-columns: 236px minmax(0, 1fr);
  }

  .workspace {
    padding: 14px;
  }

  .dashboard-grid {
    grid-template-columns: 230px minmax(0, 1fr) 260px;
  }
}

@media (max-width: 1180px) {
  html,
  body,
  #app {
    overflow: auto;
  }

  .app-shell,
  .workspace {
    height: auto;
    min-height: 100vh;
    overflow: visible;
  }

  .hero-row,
  .dashboard-grid {
    grid-template-columns: 1fr;
  }

  .left-column {
    grid-template-rows: auto auto;
  }
}
</style>
