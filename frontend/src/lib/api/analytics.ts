import { eventUrl, request } from "@/lib/api/client";
import { PUBLIC_RUN_EVENT_TYPES } from "@/lib/api/events";
import type {
  AnalystRun,
  CreateRunRequest,
  CreateRunResponse,
  PublicRunEvent,
  PublishReportRequest,
  PublishReportResponse,
  ReportPreview,
  ReportPreviewRequest,
  ReportTemplate,
  RerunMetric,
  TemplateSuitabilityOverview,
} from "@/types/analytics";

const base = (workspaceId: string) => `/api/v1/workspaces/${workspaceId}/analytics`;

export const analyticsApi = {
  createRun: (workspaceId: string, payload: CreateRunRequest) =>
    request<CreateRunResponse>(`${base(workspaceId)}/runs`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getRun: (workspaceId: string, runId: string) => request<AnalystRun>(`${base(workspaceId)}/runs/${runId}`),
  reportTemplates: (workspaceId: string) =>
    request<{ items: ReportTemplate[] }>(`${base(workspaceId)}/report-templates`),
  rerunMetrics: (workspaceId: string) => request<{ items: RerunMetric[] }>(`${base(workspaceId)}/metrics`),
  reportSuitability: (workspaceId: string, runId: string) =>
    request<TemplateSuitabilityOverview>(`${base(workspaceId)}/runs/${runId}/report-suitability`),
  previewReport: (workspaceId: string, runId: string, payload: ReportPreviewRequest) =>
    request<ReportPreview>(`${base(workspaceId)}/runs/${runId}/report-preview`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  publishReport: (workspaceId: string, runId: string, payload: PublishReportRequest) =>
    request<PublishReportResponse>(`${base(workspaceId)}/runs/${runId}/reports`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getEvents: (workspaceId: string, runId: string) =>
    request<{ items: PublicRunEvent[] }>(`${base(workspaceId)}/runs/${runId}/events/history`),
  streamUrl: (workspaceId: string, runId: string) => eventUrl(`${base(workspaceId)}/runs/${runId}/events`),
  connect(
    workspaceId: string,
    runId: string,
    onEvent: (event: PublicRunEvent) => void,
    onError: () => void,
  ): EventSource {
    // withCredentials: the frontend and backend are different origins in
    // dev (same host, different port), and EventSource does not attach
    // cookies cross-origin unless told to -- without this, the session
    // cookie required by `require_permission` never reaches the request.
    const source = new EventSource(analyticsApi.streamUrl(workspaceId, runId), { withCredentials: true });
    for (const type of PUBLIC_RUN_EVENT_TYPES)
      source.addEventListener(type, (message) =>
        onEvent(JSON.parse((message as MessageEvent<string>).data) as PublicRunEvent),
      );
    source.onerror = onError;
    return source;
  },
};
