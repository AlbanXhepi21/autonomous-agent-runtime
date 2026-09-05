import { cookies } from "next/headers";
import { ProfileSettings } from "@/features/settings/profile-settings";
import { LAST_WORKSPACE_COOKIE_NAME } from "@/lib/auth/constants";
import { getServerWorkspaces } from "@/lib/auth/workspaces.server";

export const metadata = { title: "Profile — Settings" };

/**
 * A profile image is a personal setting, but it is stored through the same
 * workspace-scoped artifact registry every other document goes through (see
 * `app.api.routes.workspaces.set_profile_image`) -- so this page still needs
 * *some* active workspace to upload into, even though the setting itself
 * isn't workspace-owned. Prefer the remembered one, else the caller's first
 * active membership; a person with none yet simply can't upload an image
 * until they join or create one.
 */
export default async function ProfileSettingsPage() {
  const [workspaces, cookieStore] = await Promise.all([getServerWorkspaces(), cookies()]);
  const remembered = cookieStore.get(LAST_WORKSPACE_COOKIE_NAME)?.value;
  const items = workspaces?.items ?? [];
  const rememberedWorkspace = items.find((workspace) => workspace.id === remembered && workspace.is_active);
  const uploadWorkspaceId = rememberedWorkspace?.id ?? items.find((workspace) => workspace.is_active)?.id ?? null;

  return <ProfileSettings uploadWorkspaceId={uploadWorkspaceId} />;
}
