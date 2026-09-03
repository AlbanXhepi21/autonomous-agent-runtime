import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { SESSION_COOKIE_NAME } from "@/lib/auth/constants";
import { LOGIN_RETURN_PARAM, sanitizeReturnPath } from "@/lib/auth/return-path";

/**
 * Pages reachable without a session. Everything else is protected.
 *
 * This is an optimistic, cookie-presence check only -- the session cookie is
 * HttpOnly but readable server-side here because Proxy and the backend share
 * one cookie jar under the `localhost` host in dev (cookies scope by host,
 * not port). It cannot tell an expired or revoked session from a live one;
 * the authenticated layout re-verifies against the backend before rendering
 * anything real. See `src/lib/auth/session.server.ts`.
 */
const PUBLIC_PATHS = [
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/invitations/accept",
  "/verify-email",
  "/confirm-email-change",
];

/** Pure entry points: pointless to show once a session cookie already exists. */
const REDIRECT_IF_AUTHENTICATED = new Set(["/login", "/register"]);

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const hasSessionCookie = Boolean(request.cookies.get(SESSION_COOKIE_NAME)?.value);
  const isPublicPath = PUBLIC_PATHS.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`),
  );

  if (!isPublicPath && !hasSessionCookie) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set(LOGIN_RETURN_PARAM, sanitizeReturnPath(`${pathname}${search}`));
    return NextResponse.redirect(loginUrl);
  }

  if (REDIRECT_IF_AUTHENTICATED.has(pathname) && hasSessionCookie) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
