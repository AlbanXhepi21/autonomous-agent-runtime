import { cache } from "react";
import { cookies } from "next/headers";
import { baseUrl } from "@/lib/api/client";
import { serverGet } from "@/lib/auth/server-request";
import { SESSION_COOKIE_NAME } from "@/lib/auth/constants";
import { classifyWorkspaceAccess, type WorkspaceAccess } from "@/lib/tenancy/resolve";
import type { Workspace, WorkspaceList } from "@/types/api";

export const getServerWorkspaces = cache((): Promise<WorkspaceList | null> =>
  serverGet<WorkspaceList>("/api/v1/workspaces"),
);

export type { WorkspaceAccess };

/** See `classifyWorkspaceAccess` for why this needs both the workspace list and the per-workspace lookup. */
export async function resolveWorkspaceAccess(
  workspaceId: string,
): Promise<WorkspaceAccess | { kind: "unauthenticated" }> {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE_NAME)?.value;
  if (!token) return { kind: "unauthenticated" };

  const list = await getServerWorkspaces();

  let response: Response;
  try {
    response = await fetch(`${baseUrl()}/api/v1/workspaces/${workspaceId}`, {
      headers: { Cookie: `${SESSION_COOKIE_NAME}=${token}` },
      cache: "no-store",
    });
  } catch {
    return classifyWorkspaceAccess(list?.items ?? [], workspaceId, { status: 0, workspace: null });
  }
  const body = (response.ok ? await response.json() : null) as Workspace | null;
  return classifyWorkspaceAccess(list?.items ?? [], workspaceId, {
    status: response.status,
    workspace: body,
  });
}
