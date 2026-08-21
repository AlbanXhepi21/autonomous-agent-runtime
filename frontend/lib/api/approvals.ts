import { request } from "@/lib/api/client";

export type Approval = {
  id: string; run_id: string; agent_name: string; capability: string; tool_name: string;
  resource: string | null; argument_summary: Record<string, string | number | boolean | null>;
  reason: string; status: "pending" | "approved" | "rejected" | "expired" | "cancelled";
  created_at: string; expires_at: string | null;
};

export const approvalsApi = {
  list: (runId: string) => request<Approval[]>(`/runs/${runId}/approvals`),
  approve: (id: string) => request<Approval>(`/approvals/${id}/approve`, { method: "POST" }),
  reject: (id: string) => request<Approval>(`/approvals/${id}/reject`, { method: "POST" }),
};
