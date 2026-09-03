import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { getServerUser } from "@/lib/auth/session.server";

/**
 * The secure auth gate for every authenticated route. `src/proxy.ts` already
 * redirected an unauthenticated request before it got here on the strength
 * of cookie presence alone; this re-checks against the backend so a
 * present-but-expired-or-revoked session cookie doesn't render a page that
 * looks signed in. Reaching this branch means the cookie existed but the
 * backend rejected it, so the login page explains a session expiry rather
 * than showing a bare sign-in form.
 */
export default async function AppLayout({ children }: { children: ReactNode }) {
  const user = await getServerUser();
  if (!user) redirect("/login?expired=1");
  return children;
}
