import { describe, expect, it, vi } from "vitest";
import { analyticsApi } from "./analytics";

describe("analytics API", () => {
  it("uses the configured backend URL to create a run", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ run_id: "r", conversation_id: "c", status: "running" }), { status: 202 }));
    await analyticsApi.createRun({ message: "Analyze orders" });
    expect(fetchMock).toHaveBeenCalledWith("http://api.test/api/v1/analytics/runs", expect.objectContaining({ method: "POST" }));
    fetchMock.mockRestore();
  });
});
