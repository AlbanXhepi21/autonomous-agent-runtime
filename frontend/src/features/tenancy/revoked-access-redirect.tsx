"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { TenantStateCard } from "@/features/tenancy/tenant-state-card";
import { forgetLastWorkspaceId } from "@/lib/auth/last-workspace";

/**
 * Reached when the requested workspace has no membership record at all --
 * it was removed, or the remembered workspace id was stale. The remembered
 * selection is discarded so the next visit lands on the chooser instead of
 * bouncing back here.
 */
export function RevokedAccessRedirect() {
  const router = useRouter();

  useEffect(() => {
    forgetLastWorkspaceId();
    router.replace("/");
  }, [router]);

  return (
    <TenantStateCard title="Taking you back">
      <p className="muted">This workspace is no longer available to you. Redirecting…</p>
    </TenantStateCard>
  );
}
