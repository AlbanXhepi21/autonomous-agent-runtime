"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { SettingsProvider, useSettings } from "@/features/settings/settings-context";
import { SettingsNav } from "@/features/settings/settings-nav";

function SettingsBody({ children }: { children: ReactNode }) {
  const { loading, error } = useSettings();

  return (
    <div className="settings-content">
      {loading ? (
        <div className="settings-loading">
          <span className="spinner" />
          <p>Loading settings…</p>
        </div>
      ) : error ? (
        <div className="error" role="alert">
          {error}
        </div>
      ) : (
        children
      )}
    </div>
  );
}

export function SettingsShell({
  workspaceId,
  workspaceName,
  currentUserId,
  currentUserDisplayName,
  currentUserEmail,
  children,
}: {
  workspaceId: string;
  workspaceName: string;
  currentUserId: string;
  currentUserDisplayName: string;
  currentUserEmail: string;
  children: ReactNode;
}) {
  return (
    <SettingsProvider
      workspaceId={workspaceId}
      currentUserId={currentUserId}
      currentUserDisplayName={currentUserDisplayName}
      currentUserEmail={currentUserEmail}
    >
      <div className="settings-shell">
        <header className="settings-header">
          <Link href={`/w/${workspaceId}`} className="settings-back">
            ← Back to workbench
          </Link>
          <div className="settings-header-titles">
            <h1>Organization settings</h1>
            {workspaceName ? (
              <p className="settings-header-desc">Manage {workspaceName}</p>
            ) : null}
          </div>
        </header>
        <div className="settings-body">
          <SettingsNav workspaceId={workspaceId} />
          <SettingsBody>{children}</SettingsBody>
        </div>
      </div>
    </SettingsProvider>
  );
}
