import { eventUrl, request } from "@/lib/api/client";
import { PUBLIC_RUN_EVENT_TYPES } from "@/lib/api/events";
import type { AnalystRun, CreateRunRequest, CreateRunResponse, PublicRunEvent } from "@/types/analytics";

export const analyticsApi = {
  createRun: (payload: CreateRunRequest) => request<CreateRunResponse>("/api/v1/analytics/runs", { method: "POST", body: JSON.stringify(payload) }),
  getRun: (runId: string) => request<AnalystRun>(`/api/v1/analytics/runs/${runId}`),
  getEvents: (runId: string) => request<{ items: PublicRunEvent[] }>(`/api/v1/analytics/runs/${runId}/events/history`),
  streamUrl: (runId: string) => eventUrl(`/api/v1/analytics/runs/${runId}/events`),
  connect(runId: string, onEvent: (event: PublicRunEvent) => void, onError: () => void): EventSource {
    const source = new EventSource(analyticsApi.streamUrl(runId));
    for (const type of PUBLIC_RUN_EVENT_TYPES) source.addEventListener(type, (message) => onEvent(JSON.parse((message as MessageEvent<string>).data) as PublicRunEvent));
    source.onerror = onError;
    return source;
  }
};
