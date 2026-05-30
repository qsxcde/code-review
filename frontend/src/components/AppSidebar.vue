<script setup lang="ts">
import { SwitchButton, UserFilled } from "@element-plus/icons-vue";
import type { AuthUser, NavItem } from "../types/review";

defineProps<{
  navItems: NavItem[];
  user: AuthUser | null;
}>();

const emit = defineEmits<{
  select: [key: NavItem["key"]];
  login: [];
  register: [];
  logout: [];
}>();
</script>

<template>
  <aside class="sidebar">
    <div class="brand">
      <span class="brand-mark">AI</span>
      <div>
        <strong>AI 代码评审助手</strong>
        <em>Beta</em>
      </div>
    </div>

    <nav class="nav-list">
      <button
        v-for="item in navItems"
        :key="item.key"
        class="nav-item"
        :class="{ active: item.active }"
        type="button"
        @click="emit('select', item.key)"
      >
        <el-icon><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
      </button>
    </nav>

    <div class="side-spacer" />

    <div v-if="user" class="profile">
      <span class="profile-avatar"><el-icon><UserFilled /></el-icon></span>
      <div>
        <strong>{{ user.email.split("@")[0] }}</strong>
        <em>开发工程师</em>
      </div>
      <el-button class="logout-button" text :icon="SwitchButton" @click="emit('logout')" />
    </div>
    <div v-else class="auth-actions">
      <el-button class="login-button" type="primary" @click="emit('login')">登录</el-button>
      <el-button @click="emit('register')">注册</el-button>
    </div>
  </aside>
</template>

<style scoped lang="scss">
@use "../styles/variables" as *;

.sidebar {
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 24px 14px;
  border-right: 1px solid $border;
  background: linear-gradient(180deg, #f8fbff 0%, $sidebar 100%);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 34px;
  min-width: 0;

  div {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }

  strong {
    overflow: hidden;
    color: $text;
    font-size: 14px;
    font-weight: 800;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  em {
    padding: 3px 7px;
    border-radius: 999px;
    color: $primary;
    font-size: 10px;
    font-style: normal;
    font-weight: 800;
    background: #e8eeff;
  }
}

.brand-mark {
  display: grid;
  flex: 0 0 34px;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 10px;
  color: #fff;
  font-size: 16px;
  font-weight: 900;
  background: $primary-gradient;
  box-shadow: 0 10px 22px rgba(49, 94, 251, 0.25);
}

.nav-list {
  display: grid;
  gap: 10px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 11px;
  min-height: 42px;
  padding: 0 14px;
  border: 0;
  border-radius: 8px;
  color: #536278;
  font-size: 13px;
  font-weight: 700;
  text-align: left;
  background: transparent;
  cursor: pointer;

  &.active {
    color: $primary;
    background: linear-gradient(90deg, #dfe7ff 0%, #edf2ff 100%);
    box-shadow: inset 3px 0 0 $primary;
  }
}

.side-spacer {
  flex: 1;
}

.profile {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 16px;
  border-top: 1px solid $border;

  div {
    min-width: 0;
    flex: 1;
  }

  strong,
  em {
    display: block;
  }

  strong {
    overflow: hidden;
    color: $text;
    font-size: 13px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  em {
    margin-top: 3px;
    color: $soft;
    font-size: 11px;
    font-style: normal;
  }
}

.profile-avatar {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 50%;
  color: #1d4ed8;
  background: #dbeafe;
}

.logout-button {
  flex: 0 0 auto;
  color: $muted;
}

.auth-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  padding-top: 16px;
  border-top: 1px solid $border;
}

.login-button {
  border: 0;
  background: $primary-gradient;
}
</style>
