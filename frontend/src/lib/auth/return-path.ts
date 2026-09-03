const DEFAULT_RETURN_PATH = "/";

/**
 * Restricts a caller-supplied "return to" destination to a same-app,
 * relative path. A value starting with "//" or "/\" is browser-parsed as a
 * protocol-relative URL (scheme inherited from the current page), and an
 * absolute URL naturally carries its own host -- both would send a signed-in
 * user to an attacker-controlled origin, so anything but a single-leading-
 * slash relative path falls back to the default.
 */
export function sanitizeReturnPath(candidate: string | null | undefined): string {
  if (!candidate) return DEFAULT_RETURN_PATH;
  if (!candidate.startsWith("/")) return DEFAULT_RETURN_PATH;
  if (candidate.startsWith("//") || candidate.startsWith("/\\")) return DEFAULT_RETURN_PATH;
  if (candidate.includes("://")) return DEFAULT_RETURN_PATH;
  return candidate;
}

export const LOGIN_RETURN_PARAM = "next";
