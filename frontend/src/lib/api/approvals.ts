import { request } from "@/lib/api/client";
import type { Approval } from "@/types/api";

export type { Approval };

const base = (workspaceId: string) => `/api/v1/workspaces/${workspaceId}`;

export const approvalsApi = {
  list: (workspaceId: string, runId: string) => request<Approval[]>(`${base(workspaceId)}/runs/${runId}/approvals`),
  approve: (workspaceId: string, id: string) =>
    request<Approval>(`${base(workspaceId)}/approvals/${id}/approve`, { method: "POST" }),
  reject: (workspaceId: string, id: string) =>
    request<Approval>(`${base(workspaceId)}/approvals/${id}/reject`, { method: "POST" }),
};
