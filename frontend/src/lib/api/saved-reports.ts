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

export const savedReportsApi = {
  create: (payload: SavedReportCreateRequest) =>
    request<SavedReport>("/api/v1/reports/saved", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  list: (status: "active" | "archived" | null = "active", limit = 30, offset = 0) =>
    request<SavedReportList>(
      `/api/v1/reports/saved?limit=${limit}&offset=${offset}${status ? `&status=${status}` : ""}`,
    ),
  get: (id: string) => request<SavedReport>(`/api/v1/reports/saved/${id}`),
  update: (id: string, payload: SavedReportUpdateRequest) =>
    request<SavedReport>(`/api/v1/reports/saved/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  archive: (id: string, payload: SavedReportArchiveRequest) =>
    request<SavedReport>(`/api/v1/reports/saved/${id}/archive`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  resolvedParameters: (id: string) =>
    request<SavedReportResolvedParameters>(`/api/v1/reports/saved/${id}/resolved-parameters`),
  execute: (id: string, payload: SavedReportExecuteRequest) =>
    request<SavedReportExecuteResponse>(`/api/v1/reports/saved/${id}/execute`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  executions: (id: string, limit = 20, offset = 0) =>
    request<SavedReportExecutionList>(
      `/api/v1/reports/saved/${id}/executions?limit=${limit}&offset=${offset}`,
    ),
};
