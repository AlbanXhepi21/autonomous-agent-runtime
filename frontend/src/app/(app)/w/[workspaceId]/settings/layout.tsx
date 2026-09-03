import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { SettingsShell } from "@/features/settings/settings-shell";
import { getServerUser } from "@/lib/auth/session.server";

export default async function SettingsLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ workspaceId: string }>;
}) {
  const { workspaceId } = await params;
  const user = await getServerUser();
  if (!user) redirect("/login?expired=1");

  return (
    <SettingsShell
      workspaceId={workspaceId}
      currentUserId={user.id}
      currentUserDisplayName={user.display_name}
      currentUserEmail={user.email}
    >
      {children}
    </SettingsShell>
  );
}
