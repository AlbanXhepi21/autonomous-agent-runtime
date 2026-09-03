"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { TenantStateCard } from "@/features/tenancy/tenant-state-card";
import { forgetLastWorkspaceId, rememberWorkspaceId } from "@/lib/auth/last-workspace";
import type { Workspace } from "@/types/api";

export function TenantChooser({
  workspaces,
  discardStaleSelection,
}: {
  workspaces: Workspace[];
  discardStaleSelection: boolean;
}) {
  const router = useRouter();

  useEffect(() => {
    if (discardStaleSelection) forgetLastWorkspaceId();
  }, [discardStaleSelection]);

  const open = (workspace: Workspace) => {
    rememberWorkspaceId(workspace.id);
    router.push(`/w/${workspace.id}`);
  };

  return (
    <TenantStateCard title="Choose a workspace">
      <p className="muted">Select the organization you&apos;d like to open.</p>
      <ul className="tenant-list">
        {workspaces.map((workspace) => (
          <li key={workspace.id}>
            <button type="button" onClick={() => open(workspace)} disabled={!workspace.is_active}>
              <span>{workspace.name}</span>
              {!workspace.is_active ? <span className="tenant-status">Deactivated</span> : null}
            </button>
          </li>
        ))}
      </ul>
      <div className="tenant-state-actions">
        <Link className="tenant-state-secondary" href="/organizations/new">
          Create organization
        </Link>
      </div>
    </TenantStateCard>
  );
}
