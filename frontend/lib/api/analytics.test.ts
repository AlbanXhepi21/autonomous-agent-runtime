import { describe, expect, it, vi } from "vitest";
import { analyticsApi } from "./analytics";
import { PUBLIC_RUN_EVENT_TYPES } from "./events";

describe("run event stream", () => {
  it("subscribes to every public event type the server can project", () => {
    const listeners: string[] = [];
    class FakeEventSource {
      onerror: (() => void) | null = null;
      addEventListener(type: string) { listeners.push(type); }
    }
    vi.stubGlobal("EventSource", FakeEventSource);

    analyticsApi.connect("run-1", () => {}, () => {});

    // A type the server projects but the stream never registers is delivered in
    // replayed history and dropped live, so the trace differs after a refresh.
    expect([...listeners].sort()).toEqual([...PUBLIC_RUN_EVENT_TYPES].sort());
    vi.unstubAllGlobals();
  });
});

describe("analytics API", () => {
  it("uses the configured backend URL to create a run", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ run_id: "r", conversation_id: "c", status: "running" }), { status: 202 }));
    await analyticsApi.createRun({ message: "Analyze orders" });
    expect(fetchMock).toHaveBeenCalledWith("http://api.test/api/v1/analytics/runs", expect.objectContaining({ method: "POST" }));
    fetchMock.mockRestore();
  });
});
