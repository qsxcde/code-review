import { computed, ref } from "vue";
import { ElMessage } from "element-plus";
import {
  clearAuthSession,
  loadAuthSession,
  login,
  logout,
  register,
  saveAuthSession,
} from "../api/authApi";
import type { AuthSession } from "../types/auth";

export const useAuth = (apiBaseUrl: string) => {
  const authSession = ref<AuthSession | null>(loadAuthSession());
  const authDialogVisible = ref(false);
  const authMode = ref<"login" | "register">("login");
  const authEmail = ref("");
  const authPassword = ref("");
  const authLoading = ref(false);
  const currentAccessToken = computed(() => authSession.value?.access_token || "");

  const openAuthDialog = (mode: "login" | "register") => {
    authMode.value = mode;
    authDialogVisible.value = true;
  };

  const expireSession = () => {
    authSession.value = null;
    clearAuthSession();
  };

  const handleAuthSubmit = async () => {
    if (!authEmail.value || !authPassword.value) {
      ElMessage.warning("请输入邮箱和密码");
      return;
    }

    authLoading.value = true;
    try {
      const nextSession = authMode.value === "login"
        ? await login(apiBaseUrl, authEmail.value, authPassword.value)
        : await register(apiBaseUrl, authEmail.value, authPassword.value);

      authSession.value = nextSession;
      saveAuthSession(nextSession);
      authDialogVisible.value = false;
      authPassword.value = "";
      ElMessage.success(authMode.value === "login" ? "登录成功" : "注册成功");
    } catch (error) {
      const message = error instanceof Error ? error.message : "认证失败";
      ElMessage.error(message);
    } finally {
      authLoading.value = false;
    }
  };

  const handleLogout = async () => {
    const session = authSession.value;
    expireSession();

    if (!session) return;

    try {
      await logout(apiBaseUrl, session.access_token, session.refresh_token);
      ElMessage.success("已登出");
    } catch (error) {
      const message = error instanceof Error ? error.message : "登出失败";
      ElMessage.warning(message);
    }
  };

  return {
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
  };
};
