import { eventUrl, request } from "@/lib/api/client";

export interface Artifact { artifact_id: string; run_id: string; name: string; type: string; size: number; created_at: string; media_type: string; metadata: Record<string, unknown>; }
export interface DatabaseTable { name: string; schema?: string; }
export interface TableDescription { name: string; schema: string; columns: Array<{ name: string; data_type: string; nullable: boolean; primary_key?: boolean }>; foreign_keys: Array<{ source_column: string; target_table: string; target_column: string }>; }
export const explorerApi = {
  artifacts: (runId?: string) => request<Artifact[]>(`/artifacts${runId ? `?run_id=${encodeURIComponent(runId)}` : ""}`),
  preview: (id: string) => request<{ content: string; truncated: boolean; media_type: string }>(`/artifacts/${id}/preview`),
  downloadUrl: (id: string) => eventUrl(`/artifacts/${id}`),
  tables: () => request<{ tables: DatabaseTable[] }>("/api/v1/schema/tables"),
  search: (query: string) => request<DatabaseTable[]>(`/api/v1/schema/search?q=${encodeURIComponent(query)}`),
  table: (name: string) => request<TableDescription>(`/api/v1/schema/tables/${encodeURIComponent(name)}`),
};
