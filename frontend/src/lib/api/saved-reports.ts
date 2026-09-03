import { request } from "@/lib/api/client";
import type {
  SavedReport,
  SavedReportArchiveRequest,
  SavedReportCreateRequest,
  SavedReportExecuteRequest,
  SavedReportExecuteResponse,
  SavedReportExecutionList,
  SavedReportList,
  SavedReportResolvedParameters,
  SavedReportUpdateRequest,
} from "@/types/saved-reports";

const base = (workspaceId: string) => `/api/v1/workspaces/${workspaceId}/reports/saved`;

export const savedReportsApi = {
  create: (workspaceId: string, payload: SavedReportCreateRequest) =>
    request<SavedReport>(base(workspaceId), {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  list: (workspaceId: string, status: "active" | "archived" | null = "active", limit = 30, offset = 0) =>
    request<SavedReportList>(
      `${base(workspaceId)}?limit=${limit}&offset=${offset}${status ? `&status=${status}` : ""}`,
    ),
  get: (workspaceId: string, id: string) => request<SavedReport>(`${base(workspaceId)}/${id}`),
  update: (workspaceId: string, id: string, payload: SavedReportUpdateRequest) =>
    request<SavedReport>(`${base(workspaceId)}/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  archive: (workspaceId: string, id: string, payload: SavedReportArchiveRequest) =>
    request<SavedReport>(`${base(workspaceId)}/${id}/archive`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  resolvedParameters: (workspaceId: string, id: string) =>
    request<SavedReportResolvedParameters>(`${base(workspaceId)}/${id}/resolved-parameters`),
  execute: (workspaceId: string, id: string, payload: SavedReportExecuteRequest) =>
    request<SavedReportExecuteResponse>(`${base(workspaceId)}/${id}/execute`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  executions: (workspaceId: string, id: string, limit = 20, offset = 0) =>
    request<SavedReportExecutionList>(`${base(workspaceId)}/${id}/executions?limit=${limit}&offset=${offset}`),
};
