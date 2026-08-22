import { request } from "@/lib/api/client";
import type { Approval } from "@/types/api";

export type { Approval };

export const approvalsApi = {
  list: (runId: string) => request<Approval[]>(`/runs/${runId}/approvals`),
  approve: (id: string) => request<Approval>(`/approvals/${id}/approve`, { method: "POST" }),
  reject: (id: string) => request<Approval>(`/approvals/${id}/reject`, { method: "POST" }),
};
