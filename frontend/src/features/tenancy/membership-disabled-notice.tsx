"use client";

import { useEffect } from "react";
import Link from "next/link";
import { TenantStateCard } from "@/features/tenancy/tenant-state-card";
import { forgetLastWorkspaceId } from "@/lib/auth/last-workspace";

export function MembershipDisabledNotice() {
  useEffect(() => {
    forgetLastWorkspaceId();
  }, []);

  return (
    <TenantStateCard title="Access disabled">
      <p className="muted">
        Your access to this workspace has been disabled by an administrator. If you believe this is
        a mistake, contact your workspace administrator.
      </p>
      <div className="tenant-state-actions">
        <Link className="tenant-state-primary" href="/">
          Go to your workspaces
        </Link>
      </div>
    </TenantStateCard>
  );
}
