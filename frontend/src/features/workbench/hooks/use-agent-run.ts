"use client";

import { useCallback, useRef, useState } from "react";
import { analyticsApi } from "@/lib/api/analytics";
import { ApiError } from "@/lib/api/client";
import type { AnalystRun, RunHistory } from "@/types/analytics";
import type { ConversationMessage } from "@/types/conversations";
import { statusFromEvent } from "@/features/workbench/status";
import { useRunStream } from "@/features/workbench/hooks/use-run-stream";

export type Message = Pick<ConversationMessage, "role" | "content" | "run_id">;

/** How long to keep asking for a result after the stream says the run finished. */
const RESULT_POLL_ATTEMPTS = 8;
const RESULT_POLL_INTERVAL_MS = 100;

interface Options {
  workspaceId: string;
  /** Called after a run settles, so the sidebar can pick up the new title. */
  onRunSettled: () => void;
  /** Called when a run pauses; returns the approval it is waiting on. */
  onApprovalRequired: (runId: string) => Promise<unknown | null>;
}

function historyFrom(run: AnalystRun): RunHistory {
  return {
    run_id: run.run_id,
    status: run.status,
    created_at: run.created_at,
    started_at: run.started_at,
    completed_at: run.finished_at,
    error: run.error,
    metrics: run.metrics,
    charts: run.charts ?? [],
    sources: run.sources ?? [],
    caveats: run.caveats ?? [],
  };
}

/**
 * Submitting a goal and collecting its result.
 *
 * The completion event and a dropped connection can both mean the run is over,
 * so settling is guarded to run once per submission.
 */
export function useAgentRun({ workspaceId, onRunSettled, onApprovalRequired }: Options) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [runs, setRuns] = useState<Record<string, RunHistory>>({});
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  //: The run currently streaming, so a live progress view can find its events
  //: without guessing which entry in `runs` is still in flight.
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const settling = useRef(false);
  const stream = useRunStream(workspaceId);

  const reset = useCallback(() => {
    stream.clear();
    settling.current = false;
    setMessages([]);
    setRuns({});
    setStatus(null);
    setError(null);
    setCurrentRunId(null);
  }, [stream]);

  /** Read the final result once, whichever signal reported the run was over. */
  const settle = useCallback(
    async (runId: string) => {
      if (settling.current) return;
      settling.current = true;
      let run: AnalystRun | undefined;
      for (let attempt = 0; attempt < RESULT_POLL_ATTEMPTS; attempt += 1) {
        run = await analyticsApi.getRun(workspaceId, runId);
        if (run.status !== "running") break;
        await new Promise((resolve) => window.setTimeout(resolve, RESULT_POLL_INTERVAL_MS));
      }
      if (!run) throw new Error("The run result was unavailable.");
      const settled = run;
      setRuns((current) => ({ ...current, [runId]: historyFrom(settled) }));
      if (settled.status === "completed" && settled.final_response) {
        setMessages((current) => [
          ...current,
          { role: "assistant", content: settled.final_response!, run_id: runId },
        ]);
      } else if (settled.status === "waiting_for_approval") {
        const pending = await onApprovalRequired(runId);
        setError(
          pending ? null : "The analyst is waiting for approval before making a protected change.",
        );
      } else {
        setError(settled.error ?? "The analyst run ended without an answer.");
      }
      setStatus(null);
      setCurrentRunId(null);
      stream.close();
      onRunSettled();
    },
    [onApprovalRequired, onRunSettled, stream, workspaceId],
  );

  /** Settle again after an approval decision released a paused run. */
  const resume = useCallback(
    async (runId: string) => {
      settling.current = false;
      await settle(runId);
    },
    [settle],
  );

  const submit = useCallback(
    async (
      message: string,
      conversationId: string | null,
      onConversation: (id: string) => void,
    ) => {
      stream.reset();
      settling.current = false;
      setError(null);
      setStatus("Analyzing…");
      setMessages((current) => [...current, { role: "user", content: message, run_id: null }]);
      try {
        const created = await analyticsApi.createRun(workspaceId, {
          message,
          ...(conversationId ? { conversation_id: conversationId } : {}),
        });
        setCurrentRunId(created.run_id);
        onConversation(created.conversation_id);
        onRunSettled();
        setRuns((current) => ({
          ...current,
          [created.run_id]: {
            run_id: created.run_id,
            status: "running",
            created_at: "",
            started_at: null,
            completed_at: null,
            error: null,
            metrics: null,
            charts: [],
            sources: [],
            caveats: [],
          },
        }));
        stream.open(created.run_id, {
          onStatus: (event) => setStatus(statusFromEvent(event)),
          onCompleted: (runId) => void settle(runId),
          onFailed: (_runId, reason) => {
            setError(reason);
            setStatus(null);
            setCurrentRunId(null);
            onRunSettled();
          },
          onDisconnected: (runId) => {
            setError("The progress stream disconnected. Checking the run status…");
            void settle(runId).catch(() => setStatus(null));
          },
        });
      } catch (cause) {
        setStatus(null);
        setCurrentRunId(null);
        setError(cause instanceof ApiError ? cause.message : "Unable to start the analyst run.");
      }
    },
    [onRunSettled, settle, stream, workspaceId],
  );

  /** Restore a conversation's transcript and the traces behind it. */
  const restore = useCallback(
    async (restored: Message[], historicalRuns: RunHistory[]) => {
      stream.reset();
      settling.current = false;
      setStatus(null);
      setError(null);
      setCurrentRunId(null);
      setMessages(restored);
      setRuns(Object.fromEntries(historicalRuns.map((run) => [run.run_id, run])));
      await stream.hydrate(historicalRuns);
    },
    [stream],
  );

  return {
    messages,
    runs,
    status,
    currentRunId,
    error,
    setError,
    eventsByRun: stream.eventsByRun,
    loadingTraces: stream.loadingTraces,
    submit,
    resume,
    restore,
    reset,
  };
}
