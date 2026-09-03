import type { Workspace } from "@/types/api";

export type TenantLanding =
  | { action: "redirect"; workspaceId: string }
  | { action: "onboarding" }
  | { action: "disabled"; workspace: Workspace }
  | { action: "chooser"; workspaces: Workspace[]; discardStale: boolean };

/**
 * Post-login tenant resolution, factored out of the (app) root page so it is
 * a plain function: one tenant opens automatically, many restore the last
 * authorized tenant or fall back to a chooser (discarding a remembered id
 * that no longer resolves to anything in the list), and none shows
 * onboarding guidance. A remembered but deactivated tenant is explained
 * rather than silently dropped.
 */
export function resolveTenantLanding(
  workspaces: Workspace[],
  rememberedId: string | undefined,
): TenantLanding {
  if (workspaces.length === 0) return { action: "onboarding" };

  if (workspaces.length === 1) {
    const only = workspaces[0];
    return only.is_active
      ? { action: "redirect", workspaceId: only.id }
      : { action: "disabled", workspace: only };
  }

  const remembered = rememberedId ? workspaces.find((item) => item.id === rememberedId) : undefined;
  if (remembered) {
    return remembered.is_active
      ? { action: "redirect", workspaceId: remembered.id }
      : { action: "disabled", workspace: remembered };
  }

  return { action: "chooser", workspaces, discardStale: Boolean(rememberedId) };
}

export type WorkspaceAccess =
  /** No membership record for this workspace at all -- removed, or never a member. */
  | { kind: "unknown" }
  | { kind: "disabled_tenant"; workspace: Workspace }
  | { kind: "membership_disabled" }
  | { kind: "ok"; workspace: Workspace };

/**
 * Resolves whether the caller may open one workspace, distinguishing cases
 * the backend's per-workspace endpoint alone cannot: it maps *both* "the
 * workspace was deactivated" and "no such workspace/membership" to the same
 * 404, by design (a caller with no standing shouldn't learn which is true).
 * `workspaces` -- every workspace the caller has any standing in, from the
 * unrestricted `GET /workspaces` list, `is_active` included -- is
 * cross-referenced against the per-workspace lookup's own status to recover
 * the distinction this UI needs in order to explain a disabled tenant safely
 * rather than just calling it "not found."
 */
export function classifyWorkspaceAccess(
  workspaces: Workspace[],
  workspaceId: string,
  perWorkspaceLookup: { status: number; workspace: Workspace | null },
): WorkspaceAccess {
  const known = workspaces.find((item) => item.id === workspaceId);
  if (!known) return { kind: "unknown" };
  if (!known.is_active) return { kind: "disabled_tenant", workspace: known };
  if (perWorkspaceLookup.status === 403) return { kind: "membership_disabled" };
  if (perWorkspaceLookup.status === 200 && perWorkspaceLookup.workspace) {
    return { kind: "ok", workspace: perWorkspaceLookup.workspace };
  }
  return { kind: "unknown" };
}
