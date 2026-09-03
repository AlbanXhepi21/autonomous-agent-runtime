/** Name of the backend's HttpOnly session cookie. Never read from JS. */
export const SESSION_COOKIE_NAME = "session_token";

/**
 * Frontend-owned, non-HttpOnly cookie remembering the last workspace the
 * user opened. It is UX state, not a credential or a duplicate of the
 * server's session -- the backend never reads it, and losing it only means
 * falling back to the tenant chooser.
 */
export const LAST_WORKSPACE_COOKIE_NAME = "last_workspace_id";
