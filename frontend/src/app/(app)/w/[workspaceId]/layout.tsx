import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { DisabledTenantNotice } from "@/features/tenancy/disabled-tenant-notice";
import { MembershipDisabledNotice } from "@/features/tenancy/membership-disabled-notice";
import { RevokedAccessRedirect } from "@/features/tenancy/revoked-access-redirect";
import { TenantSelector } from "@/features/tenancy/tenant-selector";
import { getServerUser } from "@/lib/auth/session.server";
import { resolveWorkspaceAccess } from "@/lib/auth/workspaces.server";

export default async function WorkspaceLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ workspaceId: string }>;
}) {
  const { workspaceId } = await params;
  const user = await getServerUser();
  if (!user) redirect("/login?expired=1");

  const access = await resolveWorkspaceAccess(workspaceId);
  if (access.kind === "unauthenticated") redirect("/login?expired=1");
  if (access.kind === "unknown") return <RevokedAccessRedirect />;
  if (access.kind === "membership_disabled") return <MembershipDisabledNotice />;
  if (access.kind === "disabled_tenant")
    return <DisabledTenantNotice workspace={access.workspace} />;

  return (
    <div className="app-shell">
      <header className="app-topbar">
        <div className="app-topbar-brand">
          <span className="eyebrow">Data Analyst</span>
        </div>
        <TenantSelector
          workspaceId={workspaceId}
          workspaceName={access.workspace.name}
          userId={user.id}
          userDisplayName={user.display_name}
          userEmail={user.email}
        />
      </header>
      {/* Keyed on the workspace id so switching tenants unmounts and remounts
          this subtree -- any component state or in-memory cache scoped to
          the previous tenant is discarded rather than briefly shown. */}
      <div className="app-shell-body" key={workspaceId}>
        {children}
      </div>
    </div>
  );
}
