"use client";

import { LAST_WORKSPACE_COOKIE_NAME } from "@/lib/auth/constants";

const MAX_AGE_SECONDS = 60 * 60 * 24 * 365;

export function readLastWorkspaceId(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${LAST_WORKSPACE_COOKIE_NAME}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export function rememberWorkspaceId(workspaceId: string): void {
  if (typeof document === "undefined") return;
  document.cookie = `${LAST_WORKSPACE_COOKIE_NAME}=${encodeURIComponent(workspaceId)}; path=/; max-age=${MAX_AGE_SECONDS}; samesite=lax`;
}

export function forgetLastWorkspaceId(): void {
  if (typeof document === "undefined") return;
  document.cookie = `${LAST_WORKSPACE_COOKIE_NAME}=; path=/; max-age=0; samesite=lax`;
}
