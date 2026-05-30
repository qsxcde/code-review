import { apiRequest } from "./httpClient";
import type { AuthSession } from "../types/auth";

const AUTH_STORAGE_KEY = "code-review-auth-session";

export const loadAuthSession = (): AuthSession | null => {
  const stored = window.localStorage.getItem(AUTH_STORAGE_KEY);
  if (!stored) return null;

  try {
    return JSON.parse(stored) as AuthSession;
  } catch {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    return null;
  }
};

export const saveAuthSession = (session: AuthSession) => {
  window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
};

export const clearAuthSession = () => {
  window.localStorage.removeItem(AUTH_STORAGE_KEY);
};

const submitAuth = async (
  apiBaseUrl: string,
  path: "/auth/login" | "/auth/register",
  email: string,
  password: string,
) => {
  return apiRequest<AuthSession>(apiBaseUrl, path, {
    method: "POST",
    json: { email, password },
  });
};

export const login = (apiBaseUrl: string, email: string, password: string) =>
  submitAuth(apiBaseUrl, "/auth/login", email, password);

export const register = (apiBaseUrl: string, email: string, password: string) =>
  submitAuth(apiBaseUrl, "/auth/register", email, password);

export const logout = async (apiBaseUrl: string, accessToken: string, refreshToken: string) => {
  await apiRequest<void>(apiBaseUrl, "/auth/logout", {
    method: "POST",
    accessToken,
    json: { refresh_token: refreshToken },
    okStatuses: [401],
  });
};
