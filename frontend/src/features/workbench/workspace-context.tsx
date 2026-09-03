"use client";

import { createContext, useContext, type ReactNode } from "react";

const WorkspaceIdContext = createContext<string | null>(null);

export function WorkspaceIdProvider({ workspaceId, children }: { workspaceId: string; children: ReactNode }) {
  return <WorkspaceIdContext.Provider value={workspaceId}>{children}</WorkspaceIdContext.Provider>;
}

/** The workspace every Workbench API call is scoped to. Only ever rendered inside `<Workbench workspaceId=.../>`. */
export function useWorkspaceId(): string {
  const workspaceId = useContext(WorkspaceIdContext);
  if (workspaceId === null) throw new Error("useWorkspaceId must be used within a WorkspaceIdProvider.");
  return workspaceId;
}
