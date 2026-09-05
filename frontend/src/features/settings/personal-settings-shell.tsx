"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { PersonalSettingsNav } from "@/features/settings/personal-settings-nav";
import { readLastWorkspaceId } from "@/lib/auth/last-workspace";

/**
 * The shell for `/settings/*` -- account-wide preferences that belong to the
 * signed-in person, not to any organization. Deliberately outside
 * `/w/[workspaceId]/`: unlike `SettingsShell`
 * (`features/settings/settings-shell.tsx`, the organization-settings
 * equivalent), this never fetches a workspace or its members, and its route
 * carries no `workspaceId` -- so nothing here can vary by, or get reset by,
 * switching organizations.
 */
export function PersonalSettingsShell({ children }: { children: ReactNode }) {
  // Read only for the "back" link's destination -- never to scope a
  // personal-settings request, which is why this is the one place this
  // component touches tenancy at all.
  const [backHref, setBackHref] = useState("/");

  useEffect(() => {
    // Reads a cookie, so this can only run after mount -- rendering "/" on
    // the very first client render deliberately matches the server-rendered
    // markup, then this corrects it a frame later (same reasoning as
    // `readStoredTheme()` in `appearance-settings.tsx`).
    const remembered = readLastWorkspaceId();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (remembered) setBackHref(`/w/${remembered}`);
  }, []);

  return (
    <div className="settings-shell">
      <header className="settings-header">
        <Link href={backHref} className="settings-back">
          ← Back to workbench
        </Link>
        <div className="settings-header-titles">
          <h1>Personal settings</h1>
          <p className="settings-header-desc">
            These preferences apply to your account across every organization you belong to.
          </p>
        </div>
      </header>
      <div className="settings-body">
        <PersonalSettingsNav />
        <div className="settings-content">{children}</div>
      </div>
    </div>
  );
}
