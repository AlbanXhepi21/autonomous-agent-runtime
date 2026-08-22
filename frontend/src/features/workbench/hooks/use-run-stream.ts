"use client";

import { useCallback, useRef, useState } from "react";
import { analyticsApi } from "@/lib/api/analytics";
import type { PublicRunEvent, RunHistory } from "@/types/analytics";

interface StreamHandlers {
  onStatus: (event: PublicRunEvent) => void;
  onCompleted: (runId: string) => void;
  onFailed: (runId: string, message: string) => void;
  onDisconnected: (runId: string) => void;
}

/**
 * The run progress stream and the trace events it produces.
 *
 * Owns the EventSource and the "has this run already reached a terminal event"
 * flag, which together decide whether a dropped connection means the run ended
 * or that the status still needs checking.
 */
export function useRunStream() {
  const [eventsByRun, setEventsByRun] = useState<Record<string, PublicRunEvent[]>>({});
  const [loadingTraces, setLoadingTraces] = useState<Record<string, boolean>>({});
  const source = useRef<EventSource | null>(null);
  const terminalRun = useRef<string | null>(null);

  const close = useCallback(() => {
    source.current?.close();
    source.current = null;
  }, []);

  /** Drop the connection and forget which run last reached a terminal event. */
  const reset = useCallback(() => {
    close();
    terminalRun.current = null;
  }, [close]);

  const clear = useCallback(() => {
    reset();
    setEventsByRun({});
    setLoadingTraces({});
  }, [reset]);

  const open = useCallback(
    (runId: string, handlers: StreamHandlers) => {
      setEventsByRun((current) => ({ ...current, [runId]: [] }));
      source.current = analyticsApi.connect(
        runId,
        (event) => {
          setEventsByRun((current) => ({
            ...current,
            [runId]: current[runId]?.some((existing) => existing.id === event.id)
              ? current[runId]
              : [...(current[runId] ?? []), event],
          }));
          handlers.onStatus(event);
          if (event.type === "run.completed") {
            terminalRun.current = runId;
            handlers.onCompleted(runId);
          }
          if (event.type === "run.failed") {
            terminalRun.current = runId;
            close();
            handlers.onFailed(
              runId,
              typeof event.data.error === "string" ? event.data.error : "The analyst run failed.",
            );
          }
        },
        () => {
          // A drop after a terminal event is the server closing a finished
          // stream, not a failure to recover from.
          if (terminalRun.current === runId) return;
          handlers.onDisconnected(runId);
        },
      );
    },
    [close],
  );

  /** Replay the stored traces for runs restored from conversation history. */
  const hydrate = useCallback(async (runs: RunHistory[]) => {
    setLoadingTraces(Object.fromEntries(runs.map((run) => [run.run_id, true])));
    const histories = await Promise.all(
      runs.map(
        async (run) =>
          [
            run.run_id,
            await analyticsApi
              .getEvents(run.run_id)
              .then((result) => result.items)
              .catch(() => []),
          ] as const,
      ),
    );
    setEventsByRun(Object.fromEntries(histories));
    setLoadingTraces({});
  }, []);

  return { eventsByRun, loadingTraces, open, close, reset, clear, hydrate };
}
