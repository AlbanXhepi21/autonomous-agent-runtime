import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useRunStream } from "./use-run-stream";
import { analyticsApi } from "@/lib/api/analytics";
import type { PublicRunEvent } from "@/types/analytics";

vi.mock("@/lib/api/analytics", () => ({
  analyticsApi: { connect: vi.fn(), getEvents: vi.fn() },
}));

function event(type: PublicRunEvent["type"], id = type): PublicRunEvent {
  return { id, run_id: "run-1", type, timestamp: "", data: {} };
}

/** Capture the callbacks analyticsApi.connect was given, and the closer. */
function stubConnect() {
  let emit: (event: PublicRunEvent) => void = () => {};
  let drop: () => void = () => {};
  const close = vi.fn();
  vi.mocked(analyticsApi.connect).mockImplementation((_workspaceId, _runId, onEvent, onError) => {
    emit = onEvent;
    drop = onError;
    return { close } as unknown as EventSource;
  });
  return {
    emit: (e: PublicRunEvent) => emit(e),
    drop: () => drop(),
    close,
  };
}

const handlers = () => ({
  onStatus: vi.fn(),
  onCompleted: vi.fn(),
  onFailed: vi.fn(),
  onDisconnected: vi.fn(),
});

describe("useRunStream", () => {
  beforeEach(() => vi.resetAllMocks());

  it("collects events once each and reports completion", () => {
    const socket = stubConnect();
    const on = handlers();
    const { result } = renderHook(() => useRunStream("ws-1"));

    act(() => result.current.open("run-1", on));
    act(() => socket.emit(event("sql.query_started")));
    act(() => socket.emit(event("sql.query_started")));
    act(() => socket.emit(event("run.completed")));

    expect(result.current.eventsByRun["run-1"]).toHaveLength(2);
    expect(on.onCompleted).toHaveBeenCalledWith("run-1");
  });

  it("treats a drop before any terminal event as needing a status check", () => {
    const socket = stubConnect();
    const on = handlers();
    const { result } = renderHook(() => useRunStream("ws-1"));

    act(() => result.current.open("run-1", on));
    act(() => socket.drop());

    expect(on.onDisconnected).toHaveBeenCalledWith("run-1");
  });

  it("ignores a drop after a terminal event, which is the server closing a finished stream", () => {
    const socket = stubConnect();
    const on = handlers();
    const { result } = renderHook(() => useRunStream("ws-1"));

    act(() => result.current.open("run-1", on));
    act(() => socket.emit(event("run.completed")));
    act(() => socket.drop());

    expect(on.onDisconnected).not.toHaveBeenCalled();
  });

  it("reports a failed run and closes the connection", () => {
    const socket = stubConnect();
    const on = handlers();
    const { result } = renderHook(() => useRunStream("ws-1"));

    act(() => result.current.open("run-1", on));
    act(() => socket.emit({ ...event("run.failed"), data: { error: "the query was rejected" } }));

    expect(on.onFailed).toHaveBeenCalledWith("run-1", "the query was rejected");
    expect(socket.close).toHaveBeenCalled();
  });

  it("forgets the terminal run on reset, so the next run checks its own drops", () => {
    const socket = stubConnect();
    const on = handlers();
    const { result } = renderHook(() => useRunStream("ws-1"));

    act(() => result.current.open("run-1", on));
    act(() => socket.emit(event("run.completed")));
    act(() => result.current.reset());
    act(() => result.current.open("run-1", on));
    act(() => socket.drop());

    expect(on.onDisconnected).toHaveBeenCalledWith("run-1");
  });
});
