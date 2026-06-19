import { apiFetch } from "./client";
import type { AuthStatus, TokenResponse } from "../types/api";

export function getAuthStatus(): Promise<AuthStatus> {
  return apiFetch<AuthStatus>("/auth/status");
}

export function getToken(): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/auth/token");
}

export async function logout(): Promise<void> {
  await apiFetch<unknown>("/auth/logout", { method: "POST" });
}
