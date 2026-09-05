import { redirect } from "next/navigation";

/**
 * Security is a personal setting, not an organization one -- it moved to
 * `/settings/security` (workspace-independent). This redirect exists only so
 * an old bookmark or link into the workspace-scoped URL still lands
 * somewhere useful.
 */
export default function SecuritySettingsRedirectPage() {
  redirect("/settings/security");
}
