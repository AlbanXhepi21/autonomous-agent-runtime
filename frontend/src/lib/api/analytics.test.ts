import { describe, expect, it, vi } from "vitest";
import { analyticsApi } from "./analytics";
import { PUBLIC_RUN_EVENT_TYPES } from "./events";

describe("run event stream", () => {
  it("subscribes to every public event type the server can project", () => {
    const listeners: string[] = [];
    class FakeEventSource {
      onerror: (() => void) | null = null;
      constructor(
        public url: string,
        public options?: EventSourceInit,
      ) {}
      addEventListener(type: string) {
        listeners.push(type);
      }
    }
    vi.stubGlobal("EventSource", FakeEventSource);

    analyticsApi.connect(
      "ws-1",
      "run-1",
      () => {},
      () => {},
    );

    // A type the server projects but the stream never registers is delivered in
    // replayed history and dropped live, so the trace differs after a refresh.
    expect([...listeners].sort()).toEqual([...PUBLIC_RUN_EVENT_TYPES].sort());
    vi.unstubAllGlobals();
  });

  it("attaches cookies to a cross-origin connection", () => {
    let capturedOptions: EventSourceInit | undefined;
    class FakeEventSource {
      onerror: (() => void) | null = null;
      constructor(
        public url: string,
        options?: EventSourceInit,
      ) {
        capturedOptions = options;
      }
      addEventListener() {}
    }
    vi.stubGlobal("EventSource", FakeEventSource);

    analyticsApi.connect(
      "ws-1",
      "run-1",
      () => {},
      () => {},
    );

    expect(capturedOptions).toEqual({ withCredentials: true });
    vi.unstubAllGlobals();
  });
});

describe("analytics API", () => {
  it("uses the configured backend URL to create a run", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ run_id: "r", conversation_id: "c", status: "running" }), {
        status: 202,
      }),
    );
    await analyticsApi.createRun("ws-1", { message: "Analyze orders" });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/api/v1/workspaces/ws-1/analytics/runs",
      expect.objectContaining({ method: "POST" }),
    );
    fetchMock.mockRestore();
  });
});
