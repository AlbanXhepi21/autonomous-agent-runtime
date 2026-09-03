export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
    readonly code?: string,
    readonly detail?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export const baseUrl = () => process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const CSRF_COOKIE_NAME = "csrf_token";
const CSRF_HEADER_NAME = "X-CSRF-Token";
const MUTATING_METHODS = new Set(["POST", "PATCH", "PUT", "DELETE"]);

/** Reads the non-HttpOnly CSRF cookie the backend pairs with the session cookie. */
export function readCsrfCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${CSRF_COOKIE_NAME}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string>),
  };
  if (MUTATING_METHODS.has(method) && !headers[CSRF_HEADER_NAME]) {
    const csrf = readCsrfCookie();
    if (csrf) headers[CSRF_HEADER_NAME] = csrf;
  }
  let response: Response;
  try {
    response = await fetch(`${baseUrl()}${path}`, { ...init, credentials: "include", headers });
  } catch {
    throw new ApiError("The analyst backend is unavailable. Check that FastAPI is running.");
  }
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: { code?: string; message?: string } | string;
    } | null;
    const detail =
      typeof payload?.detail === "string" ? { message: payload.detail } : payload?.detail;
    throw new ApiError(
      detail?.message ?? "The analyst request could not be completed.",
      response.status,
      typeof detail === "object" ? detail?.code : undefined,
      payload?.detail,
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const eventUrl = (path: string) => `${baseUrl()}${path}`;
