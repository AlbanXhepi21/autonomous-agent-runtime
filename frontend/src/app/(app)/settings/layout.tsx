import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { PersonalSettingsShell } from "@/features/settings/personal-settings-shell";
import { getServerUser } from "@/lib/auth/session.server";

/**
 * Account-wide settings, deliberately outside `/w/[workspaceId]/` -- see
 * `PersonalSettingsShell` for why. There is no tenant to resolve here, so
 * unlike `w/[workspaceId]/settings/layout.tsx` this never depends on an
 * active organization or its membership.
 */
export default async function PersonalSettingsLayout({ children }: { children: ReactNode }) {
  const user = await getServerUser();
  if (!user) redirect("/login?expired=1");

  return <PersonalSettingsShell>{children}</PersonalSettingsShell>;
}
