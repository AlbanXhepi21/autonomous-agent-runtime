import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { DisabledTenantNotice } from "@/features/tenancy/disabled-tenant-notice";
import { NoTenantOnboarding } from "@/features/tenancy/no-tenant-onboarding";
import { TenantChooser } from "@/features/tenancy/tenant-chooser";
import { LAST_WORKSPACE_COOKIE_NAME } from "@/lib/auth/constants";
import { getServerWorkspaces } from "@/lib/auth/workspaces.server";
import { resolveTenantLanding } from "@/lib/tenancy/resolve";

/**
 * Post-login tenant resolution. Runs server-side so the branch renders on
 * the first response rather than flashing a loading state; the branching
 * itself lives in `resolveTenantLanding` so it can be unit tested without
 * Next's server runtime.
 */
export default async function TenantResolverPage() {
  const workspaces = (await getServerWorkspaces())?.items ?? [];
  const store = await cookies();
  const remembered = store.get(LAST_WORKSPACE_COOKIE_NAME)?.value;

  const landing = resolveTenantLanding(workspaces, remembered);

  switch (landing.action) {
    case "redirect":
      redirect(`/w/${landing.workspaceId}`);
    case "onboarding":
      return <NoTenantOnboarding />;
    case "disabled":
      return <DisabledTenantNotice workspace={landing.workspace} />;
    case "chooser":
      return (
        <TenantChooser
          workspaces={landing.workspaces}
          discardStaleSelection={landing.discardStale}
        />
      );
  }
}
