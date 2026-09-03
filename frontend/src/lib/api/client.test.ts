import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, request } from "./client";

describe("request", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    document.cookie = "csrf_token=; path=/; max-age=0";
    vi.restoreAllMocks();
  });

  it("always sends credentials so the backend's session cookie is included", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));

    await request("/api/v1/auth/me");

    expect(fetchMock).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("echoes the CSRF cookie as a header on mutating requests", async () => {
    document.cookie = "csrf_token=secret-value; path=/";
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));

    await request("/api/v1/auth/logout", { method: "POST" });

    const [, init] = fetchMock.mock.calls[0];
    expect((init?.headers as Record<string, string>)["X-CSRF-Token"]).toBe("secret-value");
  });

  it("does not attach a CSRF header to a plain read", async () => {
    document.cookie = "csrf_token=secret-value; path=/";
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}", { status: 200 }));

    await request("/api/v1/auth/me");

    const [, init] = fetchMock.mock.calls[0];
    expect((init?.headers as Record<string, string>)["X-CSRF-Token"]).toBeUndefined();
  });

  it("surfaces the backend's structured error code and message", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: { code: "invalid_credentials", message: "Invalid email or password." },
        }),
        {
          status: 401,
        },
      ),
    );

    await expect(request("/api/v1/auth/login", { method: "POST" })).rejects.toMatchObject({
      name: "ApiError",
      status: 401,
      code: "invalid_credentials",
      message: "Invalid email or password.",
    });
  });

  it("reports the backend as unavailable when the network call itself fails", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("network down"));

    await expect(request("/api/v1/auth/me")).rejects.toBeInstanceOf(ApiError);
  });
});
