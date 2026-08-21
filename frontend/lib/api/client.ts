export class ApiError extends Error {
  constructor(message: string, readonly status?: number) { super(message); this.name = "ApiError"; }
}

const baseUrl = () => process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl()}${path}`, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  } catch {
    throw new ApiError("The analyst backend is unavailable. Check that FastAPI is running.");
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: { message?: string } | string } | null;
    const detail = typeof payload?.detail === "string" ? payload.detail : payload?.detail?.message;
    throw new ApiError(detail ?? "The analyst request could not be completed.", response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const eventUrl = (path: string) => `${baseUrl()}${path}`;
