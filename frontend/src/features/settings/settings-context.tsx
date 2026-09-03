"use client";

import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { membershipsApi, workspacesApi } from "@/lib/api/workspaces";
import { ApiError } from "@/lib/api/client";
import type { Membership, Role, Workspace, WorkspaceUpdateRequest } from "@/types/api";

type SettingsContextValue = {
  workspaceId: string;
  currentUserId: string;
  currentUserDisplayName: string;
  currentUserEmail: string;
  workspace: Workspace | null;
  members: Membership[] | null;
  /** The caller's own role in this workspace, once `members` has loaded. */
  role: Role | null;
  loading: boolean;
  error: string | null;
  refreshMembers: () => Promise<void>;
  /** Applies a partial edit to the workspace, using the freshest known version, and updates local state on success. */
  updateWorkspace: (
    changes: Omit<WorkspaceUpdateRequest, "expected_version">,
  ) => Promise<Workspace>;
};

const SettingsContext = createContext<SettingsContextValue | null>(null);

export function SettingsProvider({
  workspaceId,
  currentUserId,
  currentUserDisplayName,
  currentUserEmail,
  children,
}: {
  workspaceId: string;
  currentUserId: string;
  currentUserDisplayName: string;
  currentUserEmail: string;
  children: ReactNode;
}) {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [members, setMembers] = useState<Membership[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([workspacesApi.get(workspaceId), membershipsApi.list(workspaceId)])
      .then(([workspaceResult, membersResult]) => {
        if (cancelled) return;
        setWorkspace(workspaceResult);
        setMembers(membersResult.items);
      })
      .catch((loadError: unknown) => {
        if (!cancelled) {
          setError(
            loadError instanceof ApiError ? loadError.message : "Settings could not be loaded.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId]);

  const refreshMembers = useCallback(async () => {
    const result = await membershipsApi.list(workspaceId);
    setMembers(result.items);
  }, [workspaceId]);

  const updateWorkspace = useCallback(
    async (changes: Omit<WorkspaceUpdateRequest, "expected_version">) => {
      if (!workspace) throw new Error("Workspace has not loaded yet.");
      const updated = await workspacesApi.update(workspaceId, {
        ...changes,
        expected_version: workspace.version,
      });
      setWorkspace(updated);
      return updated;
    },
    [workspace, workspaceId],
  );

  const role = members?.find((membership) => membership.user_id === currentUserId)?.role ?? null;

  return (
    <SettingsContext.Provider
      value={{
        workspaceId,
        currentUserId,
        currentUserDisplayName,
        currentUserEmail,
        workspace,
        members,
        role,
        loading,
        error,
        refreshMembers,
        updateWorkspace,
      }}
    >
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings(): SettingsContextValue {
  const value = useContext(SettingsContext);
  if (!value) throw new Error("useSettings must be used within a SettingsProvider.");
  return value;
}
