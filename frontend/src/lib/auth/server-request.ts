import { cookies } from "next/headers";
import { baseUrl } from "@/lib/api/client";
import { SESSION_COOKIE_NAME } from "@/lib/auth/constants";

/**
 * A read-only, server-side fetch authenticated with the caller's session
 * cookie. Node's `fetch` has no browser cookie jar, so the header is built
 * by hand from `next/headers`. Collapses every failure (no cookie, an
 * invalid/expired session, a network error) to `null` -- callers use this
 * only to decide what to render, never to perform a mutation, so there is
 * no error detail worth preserving here.
 */
export async function serverGet<T>(path: string): Promise<T | null> {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE_NAME)?.value;
  if (!token) return null;

  let response: Response;
  try {
    response = await fetch(`${baseUrl()}${path}`, {
      headers: { Cookie: `${SESSION_COOKIE_NAME}=${token}` },
      cache: "no-store",
    });
  } catch {
    return null;
  }
  if (!response.ok) return null;
  return (await response.json()) as T;
}
