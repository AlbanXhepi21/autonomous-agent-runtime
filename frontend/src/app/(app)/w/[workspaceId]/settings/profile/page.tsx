import { redirect } from "next/navigation";

/**
 * Profile is a personal setting, not an organization one -- it moved to
 * `/settings/profile` (workspace-independent). This redirect exists only so
 * an old bookmark or link into the workspace-scoped URL still lands
 * somewhere useful.
 */
export default function ProfileSettingsRedirectPage() {
  redirect("/settings/profile");
}
