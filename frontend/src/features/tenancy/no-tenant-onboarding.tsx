import Link from "next/link";
import { TenantStateCard } from "@/features/tenancy/tenant-state-card";

export function NoTenantOnboarding() {
  return (
    <TenantStateCard title="Welcome">
      <p className="muted">
        You&apos;re not part of an organization yet. Create one to get started, or ask a teammate to
        invite you -- check your email for an invitation link.
      </p>
      <div className="tenant-state-actions">
        <Link className="tenant-state-primary" href="/organizations/new">
          Create an organization
        </Link>
      </div>
    </TenantStateCard>
  );
}
