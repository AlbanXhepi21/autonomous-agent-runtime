"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api/auth";
import { workspacesApi } from "@/lib/api/workspaces";
import { rememberWorkspaceId } from "@/lib/auth/last-workspace";
import type { Workspace } from "@/types/api";

export function TenantSelector({
  workspaceId,
  workspaceName,
  userId,
  userDisplayName,
  userEmail,
}: {
  workspaceId: string;
  workspaceName: string;
  userId: string;
  userDisplayName: string;
  userEmail: string;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [workspaces, setWorkspaces] = useState<Workspace[] | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    void workspacesApi.list().then((result) => {
      if (!cancelled) setWorkspaces(result.items);
    });
    return () => {
      cancelled = true;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node))
        setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const switchTo = (workspace: Workspace) => {
    setOpen(false);
    if (workspace.id === workspaceId) return;
    rememberWorkspaceId(workspace.id);
    router.push(`/w/${workspace.id}`);
  };

  const logout = async () => {
    setLoggingOut(true);
    try {
      await authApi.logout();
    } finally {
      router.push("/login");
    }
  };

  const others = (workspaces ?? []).filter((workspace) => workspace.id !== workspaceId);

  return (
    <div className="tenant-selector" ref={containerRef}>
      <button
        type="button"
        className="tenant-selector-trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="tenant-selector-name">{workspaceName}</span>
        <span className="tenant-selector-caret" aria-hidden="true">
          ▾
        </span>
      </button>
      {open ? (
        <div className="tenant-selector-menu" role="menu">
          <div className="tenant-selector-section">
            <p className="tenant-selector-label">Signed in as</p>
            <div style={{ padding: "4px 8px 8px", fontSize: 13 }}>
              <div style={{ fontWeight: 650 }}>{userDisplayName}</div>
              <div className="muted">{userEmail}</div>
            </div>
          </div>
          <div className="tenant-selector-section">
            <p className="tenant-selector-label">Workspaces</p>
            <button
              className="tenant-selector-option current"
              type="button"
              disabled
              role="menuitem"
            >
              <span>{workspaceName}</span>
              <span className="tenant-status">Current</span>
            </button>
            {others.map((workspace) => (
              <button
                key={workspace.id}
                type="button"
                role="menuitem"
                className="tenant-selector-option"
                disabled={!workspace.is_active}
                onClick={() => switchTo(workspace)}
              >
                <span>{workspace.name}</span>
                {!workspace.is_active ? <span className="tenant-status">Deactivated</span> : null}
              </button>
            ))}
          </div>
          <div className="tenant-selector-section">
            <Link
              className="tenant-selector-option"
              role="menuitem"
              href="/organizations/new"
              onClick={() => setOpen(false)}
            >
              Create organization
            </Link>
          </div>
          <div className="tenant-selector-section">
            <Link
              className="tenant-selector-option"
              role="menuitem"
              href="/settings/profile"
              onClick={() => setOpen(false)}
            >
              User settings
            </Link>
            <Link
              className="tenant-selector-option"
              role="menuitem"
              href={`/w/${workspaceId}/settings`}
              onClick={() => setOpen(false)}
            >
              Organization settings
            </Link>
          </div>
          <div className="tenant-selector-section">
            <button
              className="tenant-selector-option"
              role="menuitem"
              type="button"
              onClick={logout}
              disabled={loggingOut}
            >
              {loggingOut ? "Signing out…" : "Sign out"}
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
