import { eventUrl, request } from "@/lib/api/client";
import type { AnalystRun, CreateRunRequest, CreateRunResponse, PublicRunEvent } from "@/types/analytics";

export const analyticsApi = {
  createRun: (payload: CreateRunRequest) => request<CreateRunResponse>("/api/v1/analytics/runs", { method: "POST", body: JSON.stringify(payload) }),
  getRun: (runId: string) => request<AnalystRun>(`/api/v1/analytics/runs/${runId}`),
  getEvents: (runId: string) => request<{ items: PublicRunEvent[] }>(`/api/v1/analytics/runs/${runId}/events/history`),
  streamUrl: (runId: string) => eventUrl(`/api/v1/analytics/runs/${runId}/events`),
  connect(runId: string, onEvent: (event: PublicRunEvent) => void, onError: () => void): EventSource {
    const source = new EventSource(analyticsApi.streamUrl(runId));
    const eventTypes = ["run.started", "run.completed", "run.failed", "agent.started", "agent.completed", "skill.loaded", "schema.tables_listed", "schema.table_described", "sql.query_started", "sql.query_completed", "sql.query_failed", "sql.query_rejected", "python.analysis_started", "python.analysis_completed", "artifact.created", "chart.created", "report.created", "delegation.started", "delegation.completed"];
    for (const type of eventTypes) source.addEventListener(type, (message) => onEvent(JSON.parse((message as MessageEvent<string>).data) as PublicRunEvent));
    source.onerror = onError;
    return source;
  }
};
