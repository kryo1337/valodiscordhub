import { api, API_BASE_URL } from "./client";
import { useUserStore } from "@/stores/user";
import type { AuthResponse, User } from "@/types/api";

export function login() {
  window.location.href = `${API_BASE_URL}/auth/login`;
}

export async function handleCallback(code: string): Promise<AuthResponse> {
  const { data } = await api.get<AuthResponse>(`/auth/callback?code=${code}`);
  if (data.jwt) {
    localStorage.setItem("jwt", data.jwt);
    localStorage.setItem("user", JSON.stringify(data.user));
  }
  return data;
}

export function logout() {
  const store = useUserStore.getState();
  store.clearUser();
  window.location.href = "/login"; // Use full reload to clear all state
}

export function getCurrentUser(): User | null {
  const userStr = localStorage.getItem("user");
  return userStr ? JSON.parse(userStr) : null;
}

export function isAuthenticated(): boolean {
  return !!localStorage.getItem("jwt");
}

export function getToken(): string | null {
  return localStorage.getItem("jwt");
}
