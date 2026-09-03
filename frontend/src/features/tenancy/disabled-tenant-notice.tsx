import Link from "next/link";
import { TenantStateCard } from "@/features/tenancy/tenant-state-card";
import type { Workspace } from "@/types/api";

export function DisabledTenantNotice({ workspace }: { workspace: Workspace }) {
  return (
    <TenantStateCard title={`${workspace.name} is deactivated`}>
      <p className="muted">
        This organization has been deactivated and can no longer be opened. If you believe this is a
        mistake, contact the organization&apos;s owner.
      </p>
      <div className="tenant-state-actions">
        <Link className="tenant-state-primary" href="/">
          Go to your workspaces
        </Link>
      </div>
    </TenantStateCard>
  );
}
