import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { SettingsShell } from "@/features/settings/settings-shell";
import { getServerUser } from "@/lib/auth/session.server";
import { getServerWorkspaces } from "@/lib/auth/workspaces.server";

export default async function SettingsLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ workspaceId: string }>;
}) {
  const { workspaceId } = await params;
  const [user, workspaces] = await Promise.all([getServerUser(), getServerWorkspaces()]);
  if (!user) redirect("/login?expired=1");
  // Already validated by the parent `w/[workspaceId]/layout.tsx`; this is
  // only for the header's display name, so a missing lookup degrades to a
  // blank name rather than blocking the page a second time.
  const workspaceName = workspaces?.items.find((workspace) => workspace.id === workspaceId)?.name ?? "";

  return (
    <SettingsShell
      workspaceId={workspaceId}
      workspaceName={workspaceName}
      currentUserId={user.id}
      currentUserDisplayName={user.display_name}
      currentUserEmail={user.email}
    >
      {children}
    </SettingsShell>
  );
}
