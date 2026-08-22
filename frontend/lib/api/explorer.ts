import { eventUrl, request } from "@/lib/api/client";
import type {
  ArtifactMetadata,
  DatabaseSchemaSummary,
  DatabaseTable,
  TableDescription,
} from "@/types/api";

export type { ArtifactMetadata as Artifact, DatabaseTable, TableDescription };

export const explorerApi = {
  artifacts: (runId?: string) =>
    request<ArtifactMetadata[]>(`/artifacts${runId ? `?run_id=${encodeURIComponent(runId)}` : ""}`),
  preview: (id: string) =>
    request<{ content: string; truncated: boolean; media_type: string }>(
      `/artifacts/${id}/preview`,
    ),
  downloadUrl: (id: string) => eventUrl(`/artifacts/${id}`),
  tables: () => request<DatabaseSchemaSummary>("/api/v1/schema/tables"),
  search: (query: string) =>
    request<DatabaseTable[]>(`/api/v1/schema/search?q=${encodeURIComponent(query)}`),
  table: (name: string) =>
    request<TableDescription>(`/api/v1/schema/tables/${encodeURIComponent(name)}`),
};
