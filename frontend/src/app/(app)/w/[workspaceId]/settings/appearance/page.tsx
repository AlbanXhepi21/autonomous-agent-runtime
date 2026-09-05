import { redirect } from "next/navigation";

/**
 * Appearance is a personal, device-wide setting, not an organization one --
 * it moved to `/settings/appearance` (workspace-independent). This redirect
 * exists only so an old bookmark or link into the workspace-scoped URL still
 * lands somewhere useful.
 */
export default function AppearanceSettingsRedirectPage() {
  redirect("/settings/appearance");
}
