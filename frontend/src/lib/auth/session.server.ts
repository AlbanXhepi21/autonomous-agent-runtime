import { cache } from "react";
import { serverGet } from "@/lib/auth/server-request";
import type { AuthUser } from "@/types/api";

/**
 * The secure, server-side session check: asks the backend to actually
 * validate the session rather than trusting the cookie's mere presence
 * (that cheaper check happens in `src/proxy.ts` and is optimistic only).
 * Memoized per request so a layout and the page it wraps both awaiting
 * this only pay for one round trip.
 */
export const getServerUser = cache((): Promise<AuthUser | null> =>
  serverGet<AuthUser>("/api/v1/auth/me"),
);
